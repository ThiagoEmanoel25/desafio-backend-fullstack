"""AI chat endpoint: natural language in, a task for the current user out."""

import logging
import time

from fastapi import APIRouter, Depends
from pydantic_ai import UsageLimits
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import AgentDeps, ChatUnavailableError, agent
from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services import task_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ChatResponse, summary="Chat with the task agent")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    """Run the agent on the message; it may create a task for the current user.

    The tool only flushes; this route commits once after a successful run and
    rolls back on any failure, so a failed run leaves nothing behind.
    A provider error or usage-limit breach answers 503.
    """
    deps = AgentDeps(db=db, user_id=current_user.id)
    model_name = str(agent.model) if agent.model else "unknown"
    started = time.perf_counter()
    try:
        result = await agent.run(
            request.message,
            deps=deps,
            usage_limits=UsageLimits(request_limit=5, tool_calls_limit=3),
        )
        await db.commit()
    except Exception as exc:
        await db.rollback()
        logger.error(
            "chat_agent_failed",
            extra={
                "user_id": str(current_user.id),
                "error_type": type(exc).__name__,
                "model": model_name,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        raise ChatUnavailableError from None

    created_task = (
        await task_service.get_task(db, current_user.id, deps.created_task_ids[-1])
        if deps.created_task_ids
        else None
    )
    logger.info(
        "chat_agent_run",
        extra={
            "user_id": str(current_user.id),
            "model": model_name,
            "duration_ms": round((time.perf_counter() - started) * 1000),
            "tool_calls": result.usage.tool_calls,
            "tasks_created": len(deps.created_task_ids),
        },
    )
    return ChatResponse(reply=str(result.output), created_task=created_task)
