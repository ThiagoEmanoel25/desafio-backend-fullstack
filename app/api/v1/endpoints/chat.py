"""AI chat endpoints: natural language in, a task for the current user out.

`POST /v1/chat` answers JSON; `POST /v1/chat/stream` answers Server-Sent Events.
Both load the conversation from Redis (never from the client), commit once after
a successful run, roll back on failure and invalidate the task list after commit.
"""

import json
import logging
import time
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic_ai import UsageLimits
from pydantic_ai.messages import PartDeltaEvent, PartStartEvent, TextPart, TextPartDelta
from pydantic_ai.run import AgentRunResult, AgentRunResultEvent
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import history
from app.agent.agent import agent
from app.agent.deps import AgentDeps, ChatUnavailableError
from app.api.deps import get_current_user, get_db
from app.core import cache
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.schemas.task import TaskResponse
from app.services import task_service

logger = logging.getLogger(__name__)
router = APIRouter()

USAGE_LIMITS = UsageLimits(request_limit=5, tool_calls_limit=3)
UNAVAILABLE = "The assistant is unavailable, try again later"


def _model_name() -> str:
    return str(agent.model) if agent.model else "unknown"


def _ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)


async def _created_task(db: AsyncSession, deps: AgentDeps) -> TaskResponse | None:
    # Read the created row before committing: the flush already populated it.
    if not deps.created_task_ids:
        return None
    task = await task_service.get_task(db, deps.user_id, deps.created_task_ids[-1])
    return TaskResponse.model_validate(task)


async def _after_commit(
    deps: AgentDeps,
    conversation_id: uuid.UUID,
    result: AgentRunResult,
    started: float,
) -> None:
    if deps.created_task_ids:
        await cache.bump_task_list_version(deps.user_id)
    await history.save(deps.user_id, conversation_id, result.all_messages())
    logger.info(
        "chat_agent_run",
        extra={
            "user_id": str(deps.user_id),
            "model": _model_name(),
            "duration_ms": _ms(started),
            "tool_calls": result.usage.tool_calls,
            "tasks_created": len(deps.created_task_ids),
        },
    )


def _log_failure(user_id: uuid.UUID, exc: BaseException, started: float) -> None:
    logger.error(
        "chat_agent_failed",
        extra={
            "user_id": str(user_id),
            "error_type": type(exc).__name__,
            "model": _model_name(),
            "duration_ms": _ms(started),
        },
    )


@router.post("", response_model=ChatResponse, summary="Chat with the task agent")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Run the agent on the message; it may create a task for the current user.

    A provider error or usage-limit breach answers 503 and leaves nothing behind.
    """
    conversation_id = request.conversation_id or uuid.uuid4()
    deps = AgentDeps(db=db, user_id=current_user.id)
    started = time.perf_counter()
    past = await history.load(current_user.id, conversation_id)
    try:
        result = await agent.run(
            request.message,
            deps=deps,
            message_history=past,
            usage_limits=USAGE_LIMITS,
        )
        created_task = await _created_task(db, deps)
        await db.commit()
    except Exception as exc:
        await db.rollback()
        _log_failure(current_user.id, exc, started)
        raise ChatUnavailableError from None

    await _after_commit(deps, conversation_id, result, started)
    return ChatResponse(
        reply=str(result.output),
        created_task=created_task,
        conversation_id=conversation_id,
    )


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


def _text_of(event: object) -> str:
    if isinstance(event, PartStartEvent) and isinstance(event.part, TextPart):
        return event.part.content
    if isinstance(event, PartDeltaEvent) and isinstance(event.delta, TextPartDelta):
        return event.delta.content_delta
    return ""


@router.post(
    "/stream",
    summary="Chat with the task agent, streamed as Server-Sent Events",
    response_class=StreamingResponse,
)
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    """Events: `meta`, then `delta`s, then `done` (or `error`), as `data: <json>`."""
    conversation_id = request.conversation_id or uuid.uuid4()
    user_id = current_user.id
    # The request-scoped session may close before the body is streamed, so the
    # generator opens its own one, through the same (overridable) get_db.
    get_session = http_request.app.dependency_overrides.get(get_db, get_db)

    @asynccontextmanager
    async def session_scope() -> AsyncIterator[AsyncSession]:
        sessions: AsyncGenerator[AsyncSession, None] = get_session()
        try:
            yield await anext(sessions)
        finally:
            await sessions.aclose()

    async def events() -> AsyncIterator[str]:
        yield _sse({"type": "meta", "conversation_id": str(conversation_id)})
        started = time.perf_counter()
        past = await history.load(user_id, conversation_id)
        async with session_scope() as db:
            deps = AgentDeps(db=db, user_id=user_id)
            try:
                result: AgentRunResult | None = None
                async with agent.run_stream_events(
                    request.message,
                    deps=deps,
                    message_history=past,
                    usage_limits=USAGE_LIMITS,
                ) as stream:
                    async for event in stream:
                        if isinstance(event, AgentRunResultEvent):
                            result = event.result
                        elif text := _text_of(event):
                            yield _sse({"type": "delta", "text": text})
                if result is None:
                    raise RuntimeError("run ended without a result")
                created_task = await _created_task(db, deps)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                _log_failure(user_id, exc, started)
                yield _sse({"type": "error", "detail": UNAVAILABLE})
                return

        await _after_commit(deps, conversation_id, result, started)
        yield _sse(
            {
                "type": "done",
                "reply": str(result.output),
                "created_task": created_task.model_dump(mode="json")
                if created_task
                else None,
                "conversation_id": str(conversation_id),
            }
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
