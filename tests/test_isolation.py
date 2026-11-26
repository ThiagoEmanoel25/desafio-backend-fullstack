"""Per-user isolation tests: a user can never see or change another user's tasks.

Requests share one session with the test, so after each attempt the session is
expired and the row is re-read from the database.
"""

import uuid

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.models.user import User


async def _task_of(db: AsyncSession, owner: User) -> Task:
    task = Task(
        title="Secret plan", description="Private", department="Legal", user_id=owner.id
    )
    db.add(task)
    await db.commit()
    return task


async def _row(db: AsyncSession, task_id: uuid.UUID) -> Task | None:
    db.expire_all()
    return await db.get(Task, task_id)


async def test_user_cannot_list_other_user_tasks(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    other_user: User,
    db_session: AsyncSession,
):
    foreign = await _task_of(db_session, other_user)
    response = await async_client.get("/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    assert str(foreign.id) not in [t["id"] for t in response.json()]
    assert response.json() == []


async def test_user_cannot_get_other_user_task(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    other_user: User,
    db_session: AsyncSession,
):
    foreign = await _task_of(db_session, other_user)
    response = await async_client.get(f"/v1/tasks/{foreign.id}", headers=auth_headers)
    assert response.status_code == 404


async def test_user_cannot_update_other_user_task(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    other_user: User,
    db_session: AsyncSession,
):
    foreign = await _task_of(db_session, other_user)
    owner_id = other_user.id  # read before the session is expired
    response = await async_client.patch(
        f"/v1/tasks/{foreign.id}",
        json={"title": "Hijacked", "status": "completed"},
        headers=auth_headers,
    )
    assert response.status_code == 404
    row = await _row(db_session, foreign.id)
    assert row is not None
    assert (row.title, row.status, row.user_id) == (
        "Secret plan",
        "pending",
        owner_id,
    )


async def test_user_cannot_delete_other_user_task(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    other_user: User,
    db_session: AsyncSession,
):
    foreign = await _task_of(db_session, other_user)
    response = await async_client.delete(
        f"/v1/tasks/{foreign.id}", headers=auth_headers
    )
    assert response.status_code == 404
    assert await _row(db_session, foreign.id) is not None


async def test_create_task_ignores_user_id_in_body(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    user: User,
    other_user: User,
    db_session: AsyncSession,
):
    caller_id = user.id  # read before the session is expired
    response = await async_client.post(
        "/v1/tasks/",
        json={"title": "Sneaky", "department": "Ops", "user_id": str(other_user.id)},
        headers=auth_headers,
    )
    assert response.status_code == 201
    row = await _row(db_session, uuid.UUID(response.json()["id"]))
    assert row is not None
    assert row.user_id == caller_id
