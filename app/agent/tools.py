"""Tools the chat agent can call. `user_id` is read only from `ctx.deps`."""

from typing import Annotated

from pydantic import Field, ValidationError
from pydantic_ai import ModelRetry, RunContext

from app.agent.deps import AgentDeps
from app.schemas.task import (
    DEPARTMENT_MAX,
    DEPARTMENT_MIN,
    DESCRIPTION_MAX,
    TITLE_MAX,
    TITLE_MIN,
    TaskCreate,
    TaskPriority,
)
from app.services import task_service


async def create_task_tool(
    ctx: RunContext[AgentDeps],
    title: Annotated[str, Field(min_length=TITLE_MIN, max_length=TITLE_MAX)],
    department: Annotated[
        str, Field(min_length=DEPARTMENT_MIN, max_length=DEPARTMENT_MAX)
    ],
    priority: TaskPriority = TaskPriority.medium,
    description: Annotated[str | None, Field(max_length=DESCRIPTION_MAX)] = None,
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
        # Safety net: input that passes the Field limits above but fails TaskCreate.
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
