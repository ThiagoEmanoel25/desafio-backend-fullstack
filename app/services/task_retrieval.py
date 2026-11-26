"""Task search index and hybrid retrieval (Phases 9 and 10).

The corpus is only the user's own tasks (title, description, department,
priority, status). Every query filters by `user_id` in SQL first.

- Lexical channel: Postgres full-text (`ts_rank`), always available.
- Vector channel: optional; embeddings come from PydanticAI's `Embedder` using
  `settings.EMBEDDING_MODEL`. Vectors are stored as `ARRAY(Float)` (no
  pgvector), so cosine similarity is computed in Python over the user's rows.
  That is fine for the per-user task volume of this challenge, not at scale.
- Both rankings are fused with Reciprocal Rank Fusion (k=60).

Embedding failures never break a write or a search: the projection is kept
without a vector and retrieval falls back to the lexical channel.
"""

import hashlib
import logging
import math
import re
import uuid
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task import Task
from app.models.task_search_index import TS_CONFIG, TaskSearchIndex
from app.schemas.task import TaskStatus

logger = logging.getLogger(__name__)

CANDIDATES_PER_CHANNEL = 20
RRF_K = 60


def embedding_model() -> str | None:
    """The configured embedding model, or None when embeddings are disabled."""
    name = (settings.EMBEDDING_MODEL or "").strip()
    return None if name.lower() in ("", "none") else name


async def embed(texts: list[str], *, input_type: str) -> list[list[float]]:
    """Embed `texts` with the configured model (tests replace this function)."""
    from pydantic_ai import Embedder

    embedder = Embedder(embedding_model())
    if input_type == "query":
        result = await embedder.embed_query(texts)
    else:
        result = await embedder.embed_documents(texts)
    return [list(vector) for vector in result.embeddings]


def build_content(task: Task) -> str:
    """Searchable text built only from the allowed source fields."""
    parts = [
        task.title,
        task.description or "",
        task.department,
        str(getattr(task.priority, "value", task.priority)),
        str(getattr(task.status, "value", task.status)),
    ]
    return "\n".join(parts)


def source_hash(content: str) -> str:
    """sha256 of the source fields (via the content built from them)."""
    return hashlib.sha256(content.encode()).hexdigest()


async def index_task(db: AsyncSession, task: Task) -> TaskSearchIndex:
    """Create or refresh the task's projection; flushes, never commits.

    The embedding is recomputed only when `source_hash` or the model changed.
    """
    content = build_content(task)
    digest = source_hash(content)
    model = embedding_model()
    row = await db.scalar(
        select(TaskSearchIndex).where(
            TaskSearchIndex.user_id == task.user_id,
            TaskSearchIndex.task_id == task.id,
        )
    )
    if row is None:
        row = TaskSearchIndex(task_id=task.id, user_id=task.user_id)
        db.add(row)
    elif (
        row.source_hash == digest
        and row.embedding_model == model
        and (model is None or row.embedding is not None)
    ):
        return row

    row.content, row.source_hash = content, digest
    row.embedding, row.embedding_model = None, None
    if model is not None:
        try:
            row.embedding = (await embed([content], input_type="document"))[0]
            row.embedding_model = model
        except Exception:
            logger.warning(
                "task_embedding_failed",
                extra={"task_id": str(task.id), "user_id": str(task.user_id)},
                exc_info=True,
            )
    await db.flush()
    return row


async def backfill_index(db: AsyncSession) -> int:
    """Index every existing task (idempotent thanks to `source_hash`)."""
    tasks = (await db.scalars(select(Task))).all()
    for task in tasks:
        await index_task(db, task)
    return len(tasks)


@dataclass
class RetrievedTask:
    """One fused result, keeping the per-channel ranks and scores."""

    task_id: uuid.UUID
    rrf_score: float
    lexical_score: float | None = None
    vector_score: float | None = None
    lexical_rank: int | None = None
    vector_rank: int | None = None

    @property
    def origin(self) -> str:
        """'lexical', 'vector' or 'both'."""
        if self.lexical_rank is not None and self.vector_rank is not None:
            return "both"
        return "lexical" if self.lexical_rank is not None else "vector"


def rrf_fuse(
    lexical: Sequence[tuple[uuid.UUID, float]],
    vector: Sequence[tuple[uuid.UUID, float]],
    *,
    k: int = RRF_K,
) -> list[RetrievedTask]:
    """Fuse two rankings (best first) with Reciprocal Rank Fusion."""
    results: dict[uuid.UUID, RetrievedTask] = {}
    for rank, (task_id, score) in enumerate(lexical, start=1):
        item = results.setdefault(task_id, RetrievedTask(task_id, 0.0))
        item.lexical_rank, item.lexical_score = rank, score
        item.rrf_score += 1 / (k + rank)
    for rank, (task_id, score) in enumerate(vector, start=1):
        item = results.setdefault(task_id, RetrievedTask(task_id, 0.0))
        item.vector_rank, item.vector_score = rank, score
        item.rrf_score += 1 / (k + rank)
    return sorted(results.values(), key=lambda r: r.rrf_score, reverse=True)


def _cosine(a: Sequence[float], b: Sequence[float]) -> float:
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return sum(x * y for x, y in zip(a, b, strict=False)) / norm if norm else 0.0


def _scoped(
    user_id: uuid.UUID,
    exclude_task_id: uuid.UUID | None,
    statuses: Sequence[TaskStatus] | None,
):
    query = (
        select(TaskSearchIndex)
        .join(Task, Task.id == TaskSearchIndex.task_id)
        .where(TaskSearchIndex.user_id == user_id, Task.user_id == user_id)
    )
    if exclude_task_id is not None:
        query = query.where(TaskSearchIndex.task_id != exclude_task_id)
    if statuses:
        query = query.where(Task.status.in_(list(statuses)))
    return query


async def _lexical(db, query, base) -> list[tuple[uuid.UUID, float]]:
    terms = re.findall(r"\w+", query.lower())
    if not terms:
        return []
    # OR of the query words: related tasks rarely share every word.
    tsquery = func.to_tsquery(TS_CONFIG, " | ".join(dict.fromkeys(terms)))
    vector = func.to_tsvector(TS_CONFIG, TaskSearchIndex.content)
    rank = func.ts_rank(vector, tsquery)
    rows = await db.execute(
        base.with_only_columns(TaskSearchIndex.task_id, rank)
        .where(vector.op("@@")(tsquery))
        .order_by(rank.desc(), TaskSearchIndex.task_id)
        .limit(CANDIDATES_PER_CHANNEL)
    )
    return [(task_id, float(score)) for task_id, score in rows]


async def _vector(db, user_id, query, base) -> list[tuple[uuid.UUID, float]]:
    model = embedding_model()
    if model is None:
        return []
    rows = (
        await db.execute(
            base.with_only_columns(
                TaskSearchIndex.task_id, TaskSearchIndex.embedding
            ).where(
                TaskSearchIndex.embedding_model == model,
                TaskSearchIndex.embedding.is_not(None),
            )
        )
    ).all()
    if not rows:
        return []
    try:
        query_vector = (await embed([query], input_type="query"))[0]
    except Exception:
        logger.warning(
            "query_embedding_failed", extra={"user_id": str(user_id)}, exc_info=True
        )
        return []
    scored = [(task_id, _cosine(query_vector, emb)) for task_id, emb in rows]
    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:CANDIDATES_PER_CHANNEL]


async def retrieve_related_tasks(
    db: AsyncSession,
    user_id: uuid.UUID,
    query: str,
    *,
    exclude_task_id: uuid.UUID | None = None,
    statuses: Sequence[TaskStatus] | None = None,
    limit: int = 5,
) -> list[RetrievedTask]:
    """Hybrid (lexical + vector, RRF) search over the user's own tasks."""
    base = _scoped(user_id, exclude_task_id, statuses)
    lexical = await _lexical(db, query, base)
    vector = await _vector(db, user_id, query, base)
    return rrf_fuse(lexical, vector)[:limit]
