"""Task assistant service: loads the user-scoped context and runs the agent.

Read-only: it never commits. A provider failure, or output that still fails
validation after PydanticAI's retries, becomes `AssistantUnavailableError`.
Results are cached per user, task, `updated_at` and the user's task list
version (`tasks:version:{user_id}`): the related and completed tasks come from
the user's other tasks, so any task write of the user skips the old assistance.
Without Redis the cache is simply skipped.

Context: up to 5 open tasks (current work) and up to 5 similar completed tasks
(episodic memory), both from `retrieve_and_rerank` over the user's own index.
If retrieval fails, or finds no open task (e.g. unindexed rows), the open set
falls back to `list_related_open_tasks` (same department) and the completed set
to empty.
"""

import logging
import time
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.deps import AssistantDeps, AssistantUnavailableError
from app.agent.task_assistant import task_assistant
from app.config import settings
from app.core import cache
from app.models.task import Task
from app.schemas.assistance import TaskAssistance
from app.schemas.task import TaskStatus
from app.services import task_retrieval, task_service

logger = logging.getLogger(__name__)

MAX_RELATED_TASKS = 5


OPEN_STATUSES = (TaskStatus.pending, TaskStatus.in_progress)


async def _search(db, user_id, task: Task, statuses) -> list[Task]:
    results = await task_retrieval.retrieve_and_rerank(
        db,
        user_id,
        f"{task.title} {task.description or ''} {task.department}",
        department=task.department,
        priority=task.priority,
        exclude_task_id=task.id,
        statuses=statuses,
        limit=MAX_RELATED_TASKS,
    )
    return [r.task for r in results if r.task is not None]


async def _related_tasks(
    db: AsyncSession, user_id: uuid.UUID, task: Task
) -> tuple[Sequence[Task], Sequence[Task]]:
    """(open tasks, completed tasks) for the assistant; never raises."""
    try:
        async with db.begin_nested():
            open_tasks = await _search(db, user_id, task, OPEN_STATUSES)
            completed = await _search(db, user_id, task, (TaskStatus.completed,))
    except Exception:
        logger.warning(
            "assist_retrieval_failed",
            extra={"task_id": str(task.id), "user_id": str(user_id)},
            exc_info=True,
        )
        open_tasks, completed = [], []
    if not open_tasks:
        open_tasks = await task_service.list_related_open_tasks(
            db, user_id, task, limit=MAX_RELATED_TASKS
        )
    return open_tasks, completed


async def assist_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> TaskAssistance:
    """Analyse the user's task; `TaskNotFoundError` comes before any model call."""
    task = await task_service.get_task(db, user_id, task_id)
    log = {"task_id": str(task_id), "user_id": str(user_id)}
    version = await cache.task_list_version(user_id)
    key = (
        f"assist:v2:{user_id}:{task_id}:{task.updated_at.isoformat()}:{version}"
        if version is not None
        else None
    )
    if key is not None and (cached := await cache.get_value(key)) is not None:
        try:
            assistance = TaskAssistance.model_validate_json(cached)
            logger.info("task_assist_cache_hit", extra=log)
            return assistance
        except ValueError:
            logger.warning("cache_degraded", extra={"operation": "decode_assist"})
    related, completed = await _related_tasks(db, user_id, task)

    model_name = str(task_assistant.model) if task_assistant.model else "unknown"
    log["model"] = model_name
    logger.info("task_assist_requested", extra=log)
    started = time.perf_counter()
    try:
        result = await task_assistant.run(
            "Evaluate this task and help me execute it.",
            deps=AssistantDeps(
                task=task, related_tasks=related, completed_tasks=completed
            ),
        )
    except Exception as exc:
        logger.error(
            "task_assist_completed",
            extra={
                **log,
                "success": False,
                "error_type": type(exc).__name__,
                "duration_ms": round((time.perf_counter() - started) * 1000),
            },
        )
        raise AssistantUnavailableError from None
    logger.info(
        "task_assist_completed",
        extra={
            **log,
            "success": True,
            "duration_ms": round((time.perf_counter() - started) * 1000),
        },
    )
    if key is not None:
        await cache.set_value(
            key,
            result.output.model_dump_json(),
            settings.TASK_ASSIST_CACHE_TTL_SECONDS,
        )
    return result.output
