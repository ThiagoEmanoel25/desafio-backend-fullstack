"""Chat agent tests. Every run goes through TestModel / FunctionModel: no network."""

import inspect

from httpx import AsyncClient
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.agent import agent
from app.agent.tools import create_task_tool
from app.models.task import Task
from app.models.user import User

REFERENCE = (
    "Cadastre uma tarefa urgente chamada 'Revisar relatório financeiro' "
    "para o departamento Comercial"
)
REFERENCE_ARGS = {
    "title": "Revisar relatório financeiro",
    "priority": "urgent",
    "department": "Comercial",
}


def _calls_tool(*args_per_call: dict) -> FunctionModel:
    """A fake model that calls create_task_tool once per args dict, then answers."""

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        made = sum(len(m.parts) for m in messages if m.kind == "response")
        if made < len(args_per_call):
            return ModelResponse(
                parts=[ToolCallPart("create_task_tool", args_per_call[made])]
            )
        return ModelResponse(parts=[TextPart("Tarefa criada.")])

    return FunctionModel(respond)


async def _tasks(db: AsyncSession) -> list[Task]:
    return list((await db.scalars(select(Task))).all())


async def test_chat_requires_auth(async_client: AsyncClient):
    response = await async_client.post("/v1/chat/", json={"message": "oi"})
    assert response.status_code == 401


async def test_chat_rejects_empty_message(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    for message in ("", "   "):
        response = await async_client.post(
            "/v1/chat/", json={"message": message}, headers=auth_headers
        )
        assert response.status_code == 422


async def test_chat_creates_task_for_current_user(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    other_user: User,
    auth_headers: dict[str, str],
):
    with agent.override(model=TestModel()):
        response = await async_client.post(
            "/v1/chat/", json={"message": REFERENCE}, headers=auth_headers
        )
    assert response.status_code == 200
    tasks = await _tasks(db_session)
    assert len(tasks) == 1
    assert tasks[0].user_id == user.id
    assert response.json()["created_task"]["id"] == str(tasks[0].id)
    assert not [t for t in tasks if t.user_id == other_user.id]


async def test_chat_reference_message_creates_expected_task(
    async_client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
):
    # Proves the tool-to-database path with scripted arguments, not prompt quality
    # (that would need a real LLM).
    with agent.override(model=_calls_tool(REFERENCE_ARGS)):
        response = await async_client.post(
            "/v1/chat/", json={"message": REFERENCE}, headers=auth_headers
        )
    assert response.status_code == 200
    (task,) = await _tasks(db_session)
    assert (task.title, task.priority, task.department) == (
        "Revisar relatório financeiro",
        "urgent",
        "Comercial",
    )
    body = response.json()
    assert body["reply"] == "Tarefa criada."
    assert body["created_task"]["title"] == "Revisar relatório financeiro"
    assert body["created_task"]["priority"] == "urgent"
    assert body["created_task"]["department"] == "Comercial"


async def test_tool_rejects_model_supplied_user_id(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    other_user: User,
    auth_headers: dict[str, str],
):
    assert "user_id" not in inspect.signature(create_task_tool).parameters
    # The model tries to target the other user, then gives up and answers.
    with agent.override(
        model=_calls_tool({**REFERENCE_ARGS, "user_id": str(other_user.id)})
    ):
        response = await async_client.post(
            "/v1/chat/", json={"message": REFERENCE}, headers=auth_headers
        )
    assert response.status_code == 200
    assert all(t.user_id != other_user.id for t in await _tasks(db_session))


async def test_chat_handles_llm_failure(
    async_client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
):
    def boom(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("provider exploded with secret details")

    with agent.override(model=FunctionModel(boom)):
        response = await async_client.post(
            "/v1/chat/", json={"message": REFERENCE}, headers=auth_headers
        )
    assert response.status_code == 503
    assert "secret" not in response.text
    assert await _tasks(db_session) == []


async def test_chat_invalid_tool_arguments_retry(
    async_client: AsyncClient, db_session: AsyncSession, auth_headers: dict[str, str]
):
    # First call has a one-character title: ModelRetry, nothing persisted.
    # Second call is valid and persists.
    with agent.override(
        model=_calls_tool({**REFERENCE_ARGS, "title": "x"}, REFERENCE_ARGS)
    ):
        response = await async_client.post(
            "/v1/chat/", json={"message": REFERENCE}, headers=auth_headers
        )
    assert response.status_code == 200
    (task,) = await _tasks(db_session)
    assert task.title == "Revisar relatório financeiro"
