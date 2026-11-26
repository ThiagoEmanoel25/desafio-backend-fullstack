"""Task repository (data access layer).

Every method is scoped by `user_id`: there is no way to read a task by its id
alone. Like the other repositories, methods only query and `flush()`; the caller
owns the transaction and commits.
"""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.schemas.task import TaskPriority, TaskStatus


async def get_by_id(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> Task | None:
    """Return the task if it exists and belongs to `user_id`, else None."""
    return await db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )


async def list_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Task]:
    """Return the user's tasks, newest first, optionally filtered."""
    query = select(Task).where(Task.user_id == user_id)
    if status is not None:
        query = query.where(Task.status == status)
    if priority is not None:
        query = query.where(Task.priority == priority)
    result = await db.scalars(
        query.order_by(Task.created_at.desc()).offset(skip).limit(limit)
    )
    return result.all()


async def list_open_in_department(
    db: AsyncSession,
    user_id: uuid.UUID,
    department: str,
    *,
    exclude_id: uuid.UUID,
    limit: int,
) -> Sequence[Task]:
    """Return the user's non-completed tasks in `department`, newest first.

    Scoped by `user_id` and capped by `limit` in SQL, `exclude_id` left out.
    """
    result = await db.scalars(
        select(Task)
        .where(
            Task.user_id == user_id,
            Task.department == department,
            Task.status != TaskStatus.completed,
            Task.id != exclude_id,
        )
        .order_by(Task.created_at.desc(), Task.id)
        .limit(limit)
    )
    return result.all()


async def create(db: AsyncSession, task: Task) -> Task:
    """Add the task and flush so its defaults are populated (no commit)."""
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def update(db: AsyncSession, task: Task, data: dict) -> Task:
    """Apply `data` to an already user-scoped task and flush (no commit)."""
    for field, value in data.items():
        setattr(task, field, value)
    await db.flush()
    return task


async def delete(db: AsyncSession, task: Task) -> None:
    """Delete an already user-scoped task and flush (no commit)."""
    await db.delete(task)
    await db.flush()
