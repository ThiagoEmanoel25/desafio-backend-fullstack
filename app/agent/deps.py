"""Agent runtime dependencies and the controlled agent failure."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class ChatUnavailableError(Exception):
    """The agent run failed (provider error, usage limit, unexpected error)."""


@dataclass
class AgentDeps:
    """Runtime dependencies. `user_id` is here so the model can never choose it."""

    db: AsyncSession
    user_id: UUID
    created_task_ids: list[UUID] = field(default_factory=list)


class AssistantUnavailableError(Exception):
    """The task assistant run failed (provider error or invalid output)."""


@dataclass
class AssistantDeps:
    """The task under analysis and two short lists of the same user's tasks.

    `related_tasks`: open tasks (current operational context).
    `completed_tasks`: similar completed tasks (episodic memory).
    """

    task: Task
    related_tasks: Sequence[Task]
    completed_tasks: Sequence[Task] = ()
