"""Retrieval quality eval (Phase 12): Recall@5 and MRR@5 before/after rerank.

Dataset: tests/data/retrieval_eval.json (stable keys, two users). Embeddings
come from a deterministic hashing bag-of-words fake, never a provider. The run
is marked invalid if any embedding or rerank call degraded, and the test fails
if reranking lowers Recall@5. Numbers are printed (`pytest -s`) and copied to
docs/retrieval-eval.md.
"""

import hashlib
import json
import re
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user import User
from app.schemas.task import TaskCreate, TaskStatus, TaskUpdate
from app.services import task_retrieval, task_service

DATASET = Path(__file__).parent / "data" / "retrieval_eval.json"
DIMS = 64
K = 5
DEGRADED = ("task_embedding_failed", "query_embedding_failed", "rerank_failed")


async def hashing_embed(texts: list[str], *, input_type: str) -> list[list[float]]:
    vectors = []
    for text in texts:
        vector = [0.0] * DIMS
        for word in re.findall(r"\w+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % DIMS] += 1.0
        vectors.append(vector)
    return vectors


def _metrics(ranked: list[list[str]], relevant: list[list[str]]) -> tuple[float, float]:
    recall = mrr = 0.0
    for got, want in zip(ranked, relevant, strict=True):
        top = got[:K]
        recall += len(set(top) & set(want)) / len(want)
        mrr += next((1 / i for i, key in enumerate(top, 1) if key in want), 0.0)
    return recall / len(ranked), mrr / len(ranked)


async def test_rerank_does_not_lower_recall(
    db_session: AsyncSession,
    user: User,
    other_user: User,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
):
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", "fake:hashing")
    monkeypatch.setattr(task_retrieval, "embed", hashing_embed)
    data = json.loads(DATASET.read_text())
    users = {"a": user, "b": other_user}
    key_of: dict = {}
    for t in data["tasks"]:
        owner = users[t["user"]]
        task = await task_service.create_task(
            db_session,
            owner.id,
            TaskCreate(
                title=t["title"],
                description=t["description"],
                department=t["department"],
                priority=t["priority"],
            ),
        )
        if t["status"] != "pending":
            await task_service.update_task(
                db_session, owner.id, task.id, TaskUpdate(status=t["status"])
            )
        key_of[task.id] = t["key"]
    await db_session.commit()

    before, after, relevant = [], [], []
    for q in data["queries"]:
        owner = users[q["user"]]
        statuses = [TaskStatus(s) for s in q.get("statuses") or []] or None
        rrf = await task_retrieval.retrieve_related_tasks(
            db_session, owner.id, q["query"], statuses=statuses, limit=K
        )
        reranked = await task_retrieval.retrieve_and_rerank(
            db_session,
            owner.id,
            q["query"],
            department=q["department"],
            priority=q["priority"],
            statuses=statuses,
        )
        assert all(r.rerank_score is not None for r in reranked)
        before.append([key_of[r.task_id] for r in rrf])
        after.append([key_of[r.task_id] for r in reranked])
        relevant.append(q["relevant"])
        prefix = f"{q['user']}-"
        assert all(k.startswith(prefix) for k in before[-1] + after[-1])

    invalid = [m for m in DEGRADED if m in caplog.text]
    assert not invalid, f"measurement invalid, degraded: {invalid}"
    recall_b, mrr_b = _metrics(before, relevant)
    recall_a, mrr_a = _metrics(after, relevant)
    print(
        f"\nretrieval eval: {len(relevant)} queries | "
        f"RRF Recall@5={recall_b:.3f} MRR@5={mrr_b:.3f} | "
        f"reranked Recall@5={recall_a:.3f} MRR@5={mrr_a:.3f}"
    )
    assert recall_a >= recall_b
