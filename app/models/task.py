"""Task model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.schemas.task import TaskPriority, TaskStatus


def _values(enum_cls: type[TaskStatus] | type[TaskPriority]) -> list[str]:
    """Store the lowercase enum values in the database, not the member names."""
    return [member.value for member in enum_cls]


class Task(Base):
    """A task owned by exactly one user (`user_id` is the isolation boundary)."""

    __tablename__ = "tasks"
    # Fetch server-generated values (updated_at) via RETURNING on UPDATE too, so
    # reading them after a flush never triggers a lazy load in an async session.
    __mapper_args__ = {"eager_defaults": True}
    __table_args__ = (
        Index("ix_tasks_user_id", "user_id"),
        Index("ix_tasks_user_id_created_at", "user_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", values_callable=_values),
        default=TaskStatus.pending,
        server_default=TaskStatus.pending.value,
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", values_callable=_values),
        default=TaskPriority.medium,
        server_default=TaskPriority.medium.value,
    )
    department: Mapped[str] = mapped_column(String(100))
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
