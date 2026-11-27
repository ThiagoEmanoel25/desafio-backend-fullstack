"""Tools the chat agent can call. `user_id` is read only from `ctx.deps`."""

from datetime import date
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
    TaskStatus,
)
from app.services import task_retrieval, task_service


async def create_task_tool(
    ctx: RunContext[AgentDeps],
    title: Annotated[str, Field(min_length=TITLE_MIN, max_length=TITLE_MAX)],
    department: Annotated[
        str, Field(min_length=DEPARTMENT_MIN, max_length=DEPARTMENT_MAX)
    ],
    priority: TaskPriority = TaskPriority.medium,
    description: Annotated[str | None, Field(max_length=DESCRIPTION_MAX)] = None,
    due_date: date | None = None,
) -> dict:
    """Create a new task owned by the current user.

    Args:
        title: Short task title, 3 to 200 characters.
        department: Department responsible for the task, 2 to 100 characters,
            exactly as the user named it. Never invent one.
        priority: One of low, medium, high, urgent.
        description: Optional details, up to 2000 characters.
        due_date: Deadline in YYYY-MM-DD format, only when requested by the user.
    """
    try:
        data = TaskCreate(
            title=title,
            department=department,
            priority=priority,
            description=description,
            due_date=due_date,
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
        "due_date": task.due_date.isoformat() if task.due_date else None,
    }


LIST_TASKS_MAX = 10


async def list_tasks(
    ctx: RunContext[AgentDeps],
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    limit: Annotated[int, Field(ge=1, le=LIST_TASKS_MAX)] = LIST_TASKS_MAX,
) -> list[dict]:
    """List the current user's most recent tasks (at most 10).

    Args:
        status: Optional filter: pending, in_progress or completed.
        priority: Optional filter: low, medium, high or urgent.
        limit: How many tasks to return, 1 to 10.
    """
    tasks = await task_service.list_tasks(
        ctx.deps.db,
        ctx.deps.user_id,
        status=status,
        priority=priority,
        limit=min(limit, LIST_TASKS_MAX),
    )
    return [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "department": t.department,
        }
        for t in tasks
    ]


MEMORY_QUERY_MAX = 200
MEMORY_LIMIT_MAX = 5
MEMORY_SNIPPET_MAX = 160


async def search_task_memory(
    ctx: RunContext[AgentDeps],
    query: Annotated[str, Field(min_length=2, max_length=MEMORY_QUERY_MAX)],
    status: TaskStatus | None = None,
    limit: Annotated[int, Field(ge=1, le=MEMORY_LIMIT_MAX)] = MEMORY_LIMIT_MAX,
) -> list[dict]:
    """Search the current user's own tasks by topic (read only, at most 5).

    Use it for past or similar work; status=completed finds finished tasks.

    Args:
        query: What to look for, up to 200 characters.
        status: Optional filter: pending, in_progress or completed.
        limit: How many tasks to return, 1 to 5.
    """
    results = await task_retrieval.retrieve_and_rerank(
        ctx.deps.db,
        ctx.deps.user_id,
        query[:MEMORY_QUERY_MAX],
        statuses=[status] if status else None,
        limit=min(limit, MEMORY_LIMIT_MAX),
    )
    return [
        {
            "task_id": str(t.id),
            "title": t.title,
            "status": t.status,
            "priority": t.priority,
            "department": t.department,
            "description": (t.description or "")[:MEMORY_SNIPPET_MAX],
        }
        for t in (r.task for r in results)
        if t is not None
    ]
