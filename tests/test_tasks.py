"""Task CRUD tests."""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task

PAYLOAD = {
    "title": "Write report",
    "description": "Quarterly numbers",
    "priority": "high",
    "department": "Finance",
}


async def _create(client: AsyncClient, headers: dict[str, str], **overrides) -> dict:
    response = await client.post(
        "/v1/tasks/", json={**PAYLOAD, **overrides}, headers=headers
    )
    assert response.status_code == 201
    return response.json()


async def test_create_task(async_client: AsyncClient, auth_headers: dict[str, str]):
    response = await async_client.post("/v1/tasks/", json=PAYLOAD, headers=auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert {k: body[k] for k in PAYLOAD} == PAYLOAD
    assert body["status"] == "pending"
    assert "user_id" not in body


async def test_create_task_invalid_payload(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    short_title = await async_client.post(
        "/v1/tasks/", json={**PAYLOAD, "title": "ab"}, headers=auth_headers
    )
    bad_priority = await async_client.post(
        "/v1/tasks/", json={**PAYLOAD, "priority": "bogus"}, headers=auth_headers
    )
    assert short_title.status_code == 422
    assert bad_priority.status_code == 422


async def test_create_task_requires_auth(async_client: AsyncClient):
    response = await async_client.post("/v1/tasks/", json=PAYLOAD)
    assert response.status_code == 401


async def test_list_tasks_returns_own_tasks(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    for title in ("First task", "Second task", "Third task"):
        await _create(async_client, auth_headers, title=title)
    response = await async_client.get("/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    assert [t["title"] for t in response.json()] == [
        "Third task",
        "Second task",
        "First task",
    ]


async def test_list_tasks_filters_by_status_and_priority(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    await _create(async_client, auth_headers, title="Low one", priority="low")
    done = await _create(async_client, auth_headers, title="High done", priority="high")
    await _create(async_client, auth_headers, title="High open", priority="high")
    await async_client.patch(
        f"/v1/tasks/{done['id']}", json={"status": "completed"}, headers=auth_headers
    )

    by_status = await async_client.get(
        "/v1/tasks/", params={"status": "completed"}, headers=auth_headers
    )
    by_priority = await async_client.get(
        "/v1/tasks/", params={"priority": "high"}, headers=auth_headers
    )
    both = await async_client.get(
        "/v1/tasks/",
        params={"priority": "high", "status": "pending"},
        headers=auth_headers,
    )
    assert [t["title"] for t in by_status.json()] == ["High done"]
    assert {t["title"] for t in by_priority.json()} == {"High done", "High open"}
    assert [t["title"] for t in both.json()] == ["High open"]
    junk = await async_client.get(
        "/v1/tasks/", params={"status": "nope"}, headers=auth_headers
    )
    assert junk.status_code == 422


async def test_list_tasks_respects_skip_and_limit(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    for title in ("Task one", "Task two", "Task three"):
        await _create(async_client, auth_headers, title=title)
    page = await async_client.get(
        "/v1/tasks/", params={"skip": 1, "limit": 1}, headers=auth_headers
    )
    assert [t["title"] for t in page.json()] == ["Task two"]
    for limit in (0, 101):
        bad = await async_client.get(
            "/v1/tasks/", params={"limit": limit}, headers=auth_headers
        )
        assert bad.status_code == 422
    negative = await async_client.get(
        "/v1/tasks/", params={"skip": -1}, headers=auth_headers
    )
    assert negative.status_code == 422


async def test_get_task(async_client: AsyncClient, auth_headers: dict[str, str]):
    created = await _create(async_client, auth_headers)
    response = await async_client.get(
        f"/v1/tasks/{created['id']}", headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == created


async def test_get_task_unknown_id(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    response = await async_client.get(f"/v1/tasks/{uuid.uuid4()}", headers=auth_headers)
    assert response.status_code == 404
    malformed = await async_client.get("/v1/tasks/not-a-uuid", headers=auth_headers)
    assert malformed.status_code == 422


async def test_update_task_partial(
    async_client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
):
    created = await _create(async_client, auth_headers)
    response = await async_client.patch(
        f"/v1/tasks/{created['id']}",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    db_session.expire_all()
    row = await db_session.get(Task, uuid.UUID(created["id"]))
    assert row is not None
    assert row.status == "in_progress"
    assert (row.title, row.description, row.priority, row.department) == (
        PAYLOAD["title"],
        PAYLOAD["description"],
        PAYLOAD["priority"],
        PAYLOAD["department"],
    )


async def test_update_task_explicit_null_is_rejected(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    created = await _create(async_client, auth_headers)
    for field in ("title", "department", "status", "priority"):
        response = await async_client.patch(
            f"/v1/tasks/{created['id']}", json={field: None}, headers=auth_headers
        )
        assert response.status_code == 422, field


async def test_update_task_can_clear_description(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    created = await _create(async_client, auth_headers)
    response = await async_client.patch(
        f"/v1/tasks/{created['id']}", json={"description": None}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["description"] is None


async def test_delete_task(async_client: AsyncClient, auth_headers: dict[str, str]):
    created = await _create(async_client, auth_headers)
    response = await async_client.delete(
        f"/v1/tasks/{created['id']}", headers=auth_headers
    )
    assert response.status_code == 204
    assert response.content == b""
    again = await async_client.get(f"/v1/tasks/{created['id']}", headers=auth_headers)
    assert again.status_code == 404
