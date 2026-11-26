"""Task service: the single rule set shared by the API and the agent tools.

Every function is scoped by `user_id`. A task that is missing and a task owned
by someone else are indistinguishable: both raise `TaskNotFoundError`.
Functions flush but never commit; the caller owns the transaction.
"""

import logging
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories import task_repository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate

logger = logging.getLogger(__name__)


class TaskNotFoundError(Exception):
    """The task does not exist or does not belong to the user."""


async def create_task(db: AsyncSession, user_id: uuid.UUID, data: TaskCreate) -> Task:
    """Create a task owned by `user_id`."""
    task = await task_repository.create(db, Task(**data.model_dump(), user_id=user_id))
    logger.info(
        "task_created", extra={"task_id": str(task.id), "user_id": str(user_id)}
    )
    return task


async def list_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    *,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    skip: int = 0,
    limit: int = 20,
) -> Sequence[Task]:
    """List the user's tasks, newest first."""
    return await task_repository.list_by_user(
        db, user_id, status=status, priority=priority, skip=skip, limit=limit
    )


async def list_related_open_tasks(
    db: AsyncSession, user_id: uuid.UUID, task: Task, *, limit: int
) -> Sequence[Task]:
    """Other open tasks of the user in the same department as `task`."""
    return await task_repository.list_open_in_department(
        db, user_id, task.department, exclude_id=task.id, limit=limit
    )


async def get_task(db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> Task:
    """Return the user's task or raise `TaskNotFoundError`."""
    task = await task_repository.get_by_id(db, user_id, task_id)
    if task is None:
        raise TaskNotFoundError(task_id)
    return task


async def update_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID, data: TaskUpdate
) -> Task:
    """Apply only the fields the caller sent."""
    task = await get_task(db, user_id, task_id)
    return await task_repository.update(db, task, data.model_dump(exclude_unset=True))


async def delete_task(db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID) -> None:
    """Delete the user's task or raise `TaskNotFoundError`."""
    await task_repository.delete(db, await get_task(db, user_id, task_id))
