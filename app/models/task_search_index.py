"""Search projection of a task (Phase 9).

A derived, rebuildable row per task: never a source of truth and never fed by
chat messages or AI answers. Without pgvector the embedding is stored as a
plain `ARRAY(Float)` and cosine similarity is computed in Python (fine for the
task count of one user in this challenge, not for large corpora).
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

# 'simple' config: no stemming or stop words, so it works the same for
# Portuguese and English task text and for department names / enum values.
TS_CONFIG = "simple"


class TaskSearchIndex(Base):
    """Searchable content, source hash and optional embedding of one task."""

    __tablename__ = "task_search_index"
    __table_args__ = (
        UniqueConstraint("user_id", "task_id", name="uq_task_search_index_user_task"),
        Index(
            "ix_task_search_index_content_fts",
            text(f"to_tsvector('{TS_CONFIG}', content)"),
            postgresql_using="gin",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    task_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE")
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE")
    )
    content: Mapped[str] = mapped_column(Text)
    source_hash: Mapped[str] = mapped_column(String(64))
    embedding: Mapped[list[float] | None] = mapped_column(ARRAY(Float))
    embedding_model: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
