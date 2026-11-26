"""Agent runtime dependencies and the controlled agent failure."""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ChatUnavailableError(Exception):
    """The agent run failed (provider error, usage limit, unexpected error)."""


@dataclass
class AgentDeps:
    """Runtime dependencies. `user_id` is here so the model can never choose it."""

    db: AsyncSession
    user_id: UUID
    created_task_ids: list[UUID] = field(default_factory=list)
