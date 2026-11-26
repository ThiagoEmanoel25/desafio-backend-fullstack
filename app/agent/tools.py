"""Tools the chat agent can call. `user_id` is read only from `ctx.deps`."""

from dataclasses import dataclass, field
from typing import Annotated
from uuid import UUID

from pydantic import Field, ValidationError
from pydantic_ai import ModelRetry, RunContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.task import TaskCreate, TaskPriority
from app.services import task_service


@dataclass
class AgentDeps:
    """Runtime dependencies. `user_id` is here so the model can never choose it.

    Defined next to the tool that reads it (agent.py re-exports it) because
    PydanticAI resolves the tool's annotations at registration time.
    """

    db: AsyncSession
    user_id: UUID
    created_task_ids: list[UUID] = field(default_factory=list)


async def create_task_tool(
    ctx: RunContext[AgentDeps],
    title: Annotated[str, Field(min_length=3, max_length=200)],
    department: Annotated[str, Field(min_length=2, max_length=100)],
    priority: TaskPriority = TaskPriority.medium,
    description: Annotated[str | None, Field(max_length=2000)] = None,
) -> dict:
    """Create a new task owned by the current user.

    Args:
        title: Short task title, 3 to 200 characters.
        department: Department responsible for the task, 2 to 100 characters,
            exactly as the user named it. Never invent one.
        priority: One of low, medium, high, urgent.
        description: Optional details, up to 2000 characters.
    """
    try:
        data = TaskCreate(
            title=title,
            department=department,
            priority=priority,
            description=description,
        )
    except ValidationError as exc:
        fields = ", ".join(str(e["loc"][0]) for e in exc.errors())
        raise ModelRetry(f"Invalid task fields: {fields}. Fix them and retry.") from exc
    task = await task_service.create_task(ctx.deps.db, ctx.deps.user_id, data)
    ctx.deps.created_task_ids.append(task.id)
    return {
        "task_id": str(task.id),
        "title": task.title,
        "priority": task.priority,
        "department": task.department,
    }
