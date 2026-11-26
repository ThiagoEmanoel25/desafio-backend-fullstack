"""Task assistant service: loads the user-scoped context and runs the agent.

Read-only: it never commits. A provider failure, or output that still fails
validation after PydanticAI's retries, becomes `AssistantUnavailableError`.
"""

import logging
import time
import uuid
from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.deps import AssistantDeps, AssistantUnavailableError
from app.agent.task_assistant import task_assistant
from app.models.task import Task
from app.schemas.assistance import TaskAssistance
from app.services import task_service

logger = logging.getLogger(__name__)

MAX_RELATED_TASKS = 5


async def _related_tasks(
    db: AsyncSession, user_id: uuid.UUID, task: Task
) -> Sequence[Task]:
    """Build the complementary context: the seam where retrieval will plug in."""
    return await task_service.list_related_open_tasks(
        db, user_id, task, limit=MAX_RELATED_TASKS
    )


async def assist_task(
    db: AsyncSession, user_id: uuid.UUID, task_id: uuid.UUID
) -> TaskAssistance:
    """Analyse the user's task; `TaskNotFoundError` comes before any model call."""
    task = await task_service.get_task(db, user_id, task_id)
    related = await _related_tasks(db, user_id, task)

    model_name = str(task_assistant.model) if task_assistant.model else "unknown"
    log = {"task_id": str(task_id), "user_id": str(user_id), "model": model_name}
    logger.info("task_assist_requested", extra=log)
    started = time.perf_counter()
    try:
        result = await task_assistant.run(
            "Evaluate this task and help me execute it.",
            deps=AssistantDeps(task=task, related_tasks=related),
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
    return result.output
