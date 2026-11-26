"""Conversation history, the list_tasks tool and the streaming chat.

Models are FunctionModel / TestModel and Redis is fakeredis: nothing leaves the process.
"""

import json
import uuid
from collections.abc import AsyncGenerator, AsyncIterator

import pytest
from fakeredis import FakeAsyncRedis
from httpx import AsyncClient
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import history
from app.agent.agent import agent
from app.api.deps import get_db
from app.config import settings
from app.core import cache
from app.main import app
from app.models.task import Task
from app.models.user import User
from app.services import task_service

TASK_ARGS = {"title": "Fechar o balanço", "department": "Financeiro"}


def _prompts(messages: list[ModelMessage]) -> list[str]:
    """Every user prompt the model received, oldest first."""
    return [
        p.content
        for m in messages
        if isinstance(m, ModelRequest)
        for p in m.parts
        if isinstance(p, UserPromptPart)
    ]


def _recording_model(seen: list[list[str]]) -> FunctionModel:
    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        seen.append(_prompts(messages))
        return ModelResponse(parts=[TextPart("ok")])

    return FunctionModel(respond)


async def _chat(client: AsyncClient, headers: dict, message: str, cid=None) -> dict:
    body = {"message": message}
    if cid:
        body["conversation_id"] = cid
    response = await client.post("/v1/chat", json=body, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


async def test_conversation_continues_with_history(
    async_client: AsyncClient, auth_headers: dict
):
    seen: list[list[str]] = []
    with agent.override(model=_recording_model(seen)):
        first = await _chat(async_client, auth_headers, "primeira")
        cid = first["conversation_id"]
        second = await _chat(async_client, auth_headers, "segunda", cid)
    assert uuid.UUID(cid) and second["conversation_id"] == cid
    assert seen == [["primeira"], ["primeira", "segunda"]]


async def test_user_cannot_read_another_users_conversation(
    async_client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict,
    user: User,
    other_user: User,
    fake_redis: FakeAsyncRedis,
):
    seen: list[list[str]] = []
    with agent.override(model=_recording_model(seen)):
        cid = (await _chat(async_client, auth_headers, "segredo de A"))[
            "conversation_id"
        ]
        stolen = await _chat(async_client, other_auth_headers, "sou B", cid)
    assert stolen["conversation_id"] == cid
    assert seen[1] == ["sou B"]  # B's run got only its own new message
    keys = set(await fake_redis.keys("chat:*"))
    assert keys == {f"chat:{user.id}:{cid}", f"chat:{other_user.id}:{cid}"}


async def test_history_ttl_is_applied(
    async_client: AsyncClient, auth_headers: dict, user: User, fake_redis
):
    with agent.override(model=_recording_model([])):
        cid = (await _chat(async_client, auth_headers, "oi"))["conversation_id"]
    ttl = await fake_redis.ttl(f"chat:{user.id}:{cid}")
    assert 0 < ttl <= settings.CHAT_HISTORY_TTL_SECONDS * 1.1 + 1


async def test_history_turn_limit(
    async_client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "CHAT_HISTORY_MAX_MESSAGES", 4)
    seen: list[list[str]] = []
    with agent.override(model=_recording_model(seen)):
        cid = (await _chat(async_client, auth_headers, "m1"))["conversation_id"]
        for text in ("m2", "m3", "m4"):
            await _chat(async_client, auth_headers, text, cid)
    # 4 past messages = the last 2 turns (request + response each) + the new one.
    assert seen[-1] == ["m2", "m3", "m4"]


def test_trim_never_splits_tool_call_and_return():
    call = ToolCallPart("list_tasks", {}, tool_call_id="c1")
    messages = [
        ModelRequest(parts=[UserPromptPart("a")]),
        ModelResponse(parts=[call]),
        ModelRequest(parts=[ToolReturnPart("list_tasks", [], tool_call_id="c1")]),
        ModelResponse(parts=[TextPart("x")]),
        ModelRequest(parts=[UserPromptPart("b")]),
        ModelResponse(parts=[TextPart("y")]),
    ]
    # A cut of 3 would start on the orphan tool return: it moves to the user turn.
    assert history.trim(messages, 3) == messages[4:]
    assert history.trim(messages, 6) == messages
    assert history.trim(messages[1:4], 3) == []


async def test_chat_works_without_history_when_redis_is_down(
    async_client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    down = Redis.from_url(
        "redis://127.0.0.1:1/0", socket_connect_timeout=0.2, socket_timeout=0.2
    )
    monkeypatch.setattr(cache, "_client", down)
    seen: list[list[str]] = []
    with agent.override(model=_recording_model(seen)):
        cid = (await _chat(async_client, auth_headers, "um"))["conversation_id"]
        await _chat(async_client, auth_headers, "dois", cid)
    assert seen == [["um"], ["dois"]]
    assert "cache_degraded" in caplog.text
    await down.aclose()


# --- list_tasks tool -------------------------------------------------------


async def test_list_tasks_schema_has_no_user_id():
    tool = agent._function_toolset.tools["list_tasks"]
    props = tool.tool_def.parameters_json_schema["properties"]
    assert set(props) == {"status", "priority", "limit"}
    assert props["limit"]["maximum"] == 10


async def test_list_tasks_returns_only_current_user_tasks(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    user: User,
    other_user: User,
):
    for i in range(12):
        await async_client.post(
            "/v1/tasks/",
            json={**TASK_ARGS, "title": f"Minha {i}"},
            headers=auth_headers,
        )
    db_session.add(Task(title="Alheia", department="X", user_id=other_user.id))
    await db_session.commit()

    returned: list = []

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        returns = [
            p
            for m in messages
            for p in m.parts
            if isinstance(p, ToolReturnPart) and p.tool_name == "list_tasks"
        ]
        if not returns:
            return ModelResponse(parts=[ToolCallPart("list_tasks", {"limit": 10})])
        returned.extend(returns[0].content)
        return ModelResponse(parts=[TextPart("listei")])

    with agent.override(model=FunctionModel(respond)):
        await _chat(async_client, auth_headers, "quais minhas tarefas?")
    assert len(returned) == 10
    assert all(t["title"].startswith("Minha") for t in returned)
    assert set(returned[0]) == {"id", "title", "status", "priority", "department"}


# --- streaming -------------------------------------------------------------


def _events(body: str) -> list[dict]:
    return [
        json.loads(line[len("data: ") :])
        for line in body.splitlines()
        if line.startswith("data: ")
    ]


def _streaming_tool_model() -> FunctionModel:
    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator:
        if not any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            yield {0: DeltaToolCall("create_task_tool", json.dumps(TASK_ARGS))}
            return
        for chunk in ("Tarefa ", "criada ", "com sucesso."):
            yield chunk

    return FunctionModel(stream_function=stream)


async def test_stream_requires_auth(async_client: AsyncClient):
    response = await async_client.post("/v1/chat/stream", json={"message": "oi"})
    assert response.status_code == 401


async def test_stream_creates_task_and_invalidates_list(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    user: User,
    fake_redis: FakeAsyncRedis,
):
    version_key = f"tasks:version:{user.id}"
    with agent.override(model=_streaming_tool_model()):
        response = await async_client.post(
            "/v1/chat/stream", json={"message": "crie"}, headers=auth_headers
        )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = _events(response.text)
    assert events[0]["type"] == "meta"
    deltas = [e["text"] for e in events if e["type"] == "delta"]
    assert len(deltas) >= 3
    done = events[-1]
    assert done["type"] == "done"
    assert done["reply"] == "Tarefa criada com sucesso." == "".join(deltas)
    assert done["conversation_id"] == events[0]["conversation_id"]
    (task,) = (await db_session.scalars(select(Task))).all()
    assert done["created_task"]["id"] == str(task.id) and task.user_id == user.id
    # Bumped by task_service before commit and once more after commit.
    assert int(await fake_redis.get(version_key)) == 2
    assert await fake_redis.exists(f"chat:{user.id}:{done['conversation_id']}")


async def test_stream_model_failure_sends_error_and_rolls_back(
    async_client: AsyncClient, db_session: AsyncSession, auth_headers: dict
):
    async def stream(messages: list[ModelMessage], info: AgentInfo) -> AsyncIterator:
        if not any(isinstance(p, ToolReturnPart) for m in messages for p in m.parts):
            yield {0: DeltaToolCall("create_task_tool", json.dumps(TASK_ARGS))}
            return
        yield "parcial "
        raise RuntimeError("provider exploded with secret details")

    with agent.override(model=FunctionModel(stream_function=stream)):
        response = await async_client.post(
            "/v1/chat/stream", json={"message": "crie"}, headers=auth_headers
        )
    events = _events(response.text)
    assert events[-1] == {
        "type": "error",
        "detail": "The assistant is unavailable, try again later",
    }
    assert "secret" not in response.text and "RuntimeError" not in response.text
    assert (await db_session.scalars(select(Task))).all() == []


async def test_stream_session_stays_open_until_generator_ends(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
):
    """Real get_db-like override: each session closes when its generator ends."""
    closed: dict[int, bool] = {}

    async def closing_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with AsyncSession(db_session.bind, expire_on_commit=False) as session:
            closed[id(session)] = False
            try:
                yield session
            finally:
                closed[id(session)] = True

    seen_open: list[bool] = []
    original = task_service.create_task

    async def spy(db, user_id, data):
        seen_open.append(not closed[id(db)])
        return await original(db, user_id, data)

    monkeypatch.setattr(task_service, "create_task", spy)
    app.dependency_overrides[get_db] = closing_get_db
    with agent.override(model=_streaming_tool_model()):
        response = await async_client.post(
            "/v1/chat/stream", json={"message": "crie"}, headers=auth_headers
        )
    assert _events(response.text)[-1]["type"] == "done"
    assert seen_open == [True]
    assert all(closed.values())  # every session is closed once the stream ends
    assert len((await db_session.scalars(select(Task))).all()) == 1
