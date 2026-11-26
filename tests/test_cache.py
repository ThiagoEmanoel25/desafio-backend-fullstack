"""Redis cache tests: isolation, invalidation, hits and degraded mode.

Redis is fakeredis (see `conftest.fake_redis`); models are FunctionModel /
TestModel, so nothing leaves the process.
"""

import pytest
from httpx import AsyncClient
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel
from redis.asyncio import Redis

from app.agent.agent import agent
from app.agent.task_assistant import task_assistant
from app.core import cache
from app.repositories import task_repository
from app.schemas.assistance import TaskAssistance

TASK = {"title": "Fechar o balanço", "department": "Financeiro"}


async def _version(redis: Redis, user_id) -> int:
    return int(await redis.get(f"tasks:version:{user_id}") or 0)


@pytest.fixture
def db_list_calls(monkeypatch: pytest.MonkeyPatch) -> list[int]:
    """Count how many times the list query really reaches Postgres."""
    calls: list[int] = []
    original = task_repository.list_by_user

    async def spy(*args, **kwargs):
        calls.append(1)
        return await original(*args, **kwargs)

    monkeypatch.setattr(task_repository, "list_by_user", spy)
    return calls


def _assistance_model(calls: list[int]) -> FunctionModel:
    """A fake assistant that counts its runs and returns a valid plan."""
    plan = {
        "summary": "Close the monthly books",
        "complexity": "medium",
        "estimated_hours": 4,
        "suggested_priority": "high",
        "priority_reason": "Deadline is close",
        "steps": ["Collect data"],
        "risks": [],
        "clarifying_questions": [],
    }

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        calls.append(1)
        tool = info.output_tools[0].name
        return ModelResponse(parts=[ToolCallPart(tool, plan)])

    return FunctionModel(respond)


async def test_list_cache_hit_skips_postgres_and_matches_miss(
    async_client: AsyncClient, auth_headers: dict, db_list_calls: list[int]
):
    await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    miss = await async_client.get("/v1/tasks/", headers=auth_headers)
    hit = await async_client.get("/v1/tasks/", headers=auth_headers)
    assert miss.status_code == hit.status_code == 200
    assert hit.json() == miss.json() and len(hit.json()) == 1
    assert len(db_list_calls) == 1


async def test_list_cache_never_crosses_users(
    async_client: AsyncClient,
    auth_headers: dict,
    other_auth_headers: dict,
    fake_redis: Redis,
    user,
    other_user,
):
    await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    await async_client.post(
        "/v1/tasks/", json={**TASK, "title": "Outra"}, headers=other_auth_headers
    )
    for _ in range(2):  # miss, then hit
        mine = (await async_client.get("/v1/tasks/", headers=auth_headers)).json()
        theirs = (
            await async_client.get("/v1/tasks/", headers=other_auth_headers)
        ).json()
        assert [t["title"] for t in mine] == ["Fechar o balanço"]
        assert [t["title"] for t in theirs] == ["Outra"]
    keys = await fake_redis.keys("tasks:list:*")
    assert {k.split(":")[2] for k in keys} == {str(user.id), str(other_user.id)}


async def test_filters_get_distinct_keys(
    async_client: AsyncClient, auth_headers: dict, db_list_calls: list[int]
):
    await async_client.post(
        "/v1/tasks/", json={**TASK, "priority": "urgent"}, headers=auth_headers
    )
    urgent = await async_client.get("/v1/tasks/?priority=urgent", headers=auth_headers)
    low = await async_client.get("/v1/tasks/?priority=low", headers=auth_headers)
    assert len(urgent.json()) == 1 and low.json() == []
    assert len(db_list_calls) == 2


async def test_mutations_invalidate_list(
    async_client: AsyncClient,
    auth_headers: dict,
    fake_redis: Redis,
    user,
    db_list_calls: list[int],
):
    created = await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    task_id = created.json()["id"]
    after_create = await _version(fake_redis, user.id)
    assert after_create >= 1
    await async_client.get("/v1/tasks/", headers=auth_headers)

    await async_client.patch(
        f"/v1/tasks/{task_id}", json={"status": "completed"}, headers=auth_headers
    )
    after_patch = await _version(fake_redis, user.id)
    assert after_patch > after_create
    listed = (await async_client.get("/v1/tasks/", headers=auth_headers)).json()
    assert listed[0]["status"] == "completed"

    await async_client.delete(f"/v1/tasks/{task_id}", headers=auth_headers)
    assert await _version(fake_redis, user.id) > after_patch
    assert (await async_client.get("/v1/tasks/", headers=auth_headers)).json() == []
    assert len(db_list_calls) == 3


async def test_chat_tool_create_invalidates_list(
    async_client: AsyncClient, auth_headers: dict, fake_redis: Redis, user
):
    assert (await async_client.get("/v1/tasks/", headers=auth_headers)).json() == []
    with agent.override(model=TestModel(call_tools=["create_task_tool"])):
        response = await async_client.post(
            "/v1/chat", json={"message": "crie"}, headers=auth_headers
        )
    assert response.status_code == 200
    assert await _version(fake_redis, user.id) == 1
    assert len((await async_client.get("/v1/tasks/", headers=auth_headers)).json()) == 1


async def test_assist_cache_hit_and_invalidation_on_update(
    async_client: AsyncClient, auth_headers: dict
):
    task_id = (
        await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    ).json()["id"]
    calls: list[int] = []
    url = f"/v1/tasks/{task_id}/assist"
    with task_assistant.override(model=_assistance_model(calls)):
        first = await async_client.post(url, headers=auth_headers)
        second = await async_client.post(url, headers=auth_headers)
        assert first.status_code == second.status_code == 200
        assert second.json() == first.json()
        TaskAssistance.model_validate(second.json())
        assert len(calls) == 1

        await async_client.patch(
            f"/v1/tasks/{task_id}", json={"title": "Novo título"}, headers=auth_headers
        )
        third = await async_client.post(url, headers=auth_headers)
    assert third.status_code == 200
    assert len(calls) == 2


async def test_foreign_task_assist_is_404_even_if_cached(
    async_client: AsyncClient, auth_headers: dict, other_auth_headers: dict
):
    task_id = (
        await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    ).json()["id"]
    calls: list[int] = []
    with task_assistant.override(model=_assistance_model(calls)):
        await async_client.post(f"/v1/tasks/{task_id}/assist", headers=auth_headers)
        foreign = await async_client.post(
            f"/v1/tasks/{task_id}/assist", headers=other_auth_headers
        )
    assert foreign.status_code == 404
    assert len(calls) == 1


async def test_api_works_when_redis_is_down(
    async_client: AsyncClient,
    auth_headers: dict,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    # Nothing listens on port 1: every Redis call fails fast.
    down = Redis.from_url(
        "redis://127.0.0.1:1/0", socket_connect_timeout=0.2, socket_timeout=0.2
    )
    monkeypatch.setattr(cache, "_client", down)

    created = await async_client.post("/v1/tasks/", json=TASK, headers=auth_headers)
    assert created.status_code == 201
    task_id = created.json()["id"]
    listed = await async_client.get("/v1/tasks/", headers=auth_headers)
    assert listed.status_code == 200 and len(listed.json()) == 1
    patched = await async_client.patch(
        f"/v1/tasks/{task_id}", json={"status": "completed"}, headers=auth_headers
    )
    assert patched.status_code == 200
    calls: list[int] = []
    with task_assistant.override(model=_assistance_model(calls)):
        assisted = await async_client.post(
            f"/v1/tasks/{task_id}/assist", headers=auth_headers
        )
    assert assisted.status_code == 200
    deleted = await async_client.delete(f"/v1/tasks/{task_id}", headers=auth_headers)
    assert deleted.status_code == 204
    assert "cache_degraded" in caplog.text
    await down.aclose()


async def test_cache_disabled_without_url(
    async_client: AsyncClient, auth_headers: dict, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(cache, "_client", None)
    monkeypatch.setattr(cache.settings, "REDIS_URL", "")
    assert cache.get_redis() is None
    response = await async_client.get("/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
