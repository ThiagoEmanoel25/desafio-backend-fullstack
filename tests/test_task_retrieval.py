"""Task search index and hybrid retrieval, with a fake deterministic embedder.

No real embedding provider is ever called: `task_retrieval.embed` is replaced.
"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.task_search_index import TaskSearchIndex
from app.models.user import User
from app.schemas.task import TaskCreate, TaskStatus, TaskUpdate
from app.services import task_retrieval, task_service

FAKE_MODEL = "fake:embedder"
VOCAB = ["relatório", "financeiro", "deploy", "login", "cliente", "acme"]


class FakeEmbedder:
    """Bag-of-words vector over `VOCAB`; counts calls; can be made to fail."""

    def __init__(self) -> None:
        self.calls = 0
        self.fail = False

    async def __call__(self, texts: list[str], *, input_type: str):
        self.calls += 1
        if self.fail:
            raise RuntimeError("provider down")
        return [[float(w in t.lower()) + 0.01 for w in VOCAB] for t in texts]


@pytest.fixture
def embedder(monkeypatch: pytest.MonkeyPatch) -> FakeEmbedder:
    fake = FakeEmbedder()
    monkeypatch.setattr(settings, "EMBEDDING_MODEL", FAKE_MODEL)
    monkeypatch.setattr(task_retrieval, "embed", fake)
    return fake


async def _create(db: AsyncSession, user: User, title: str, **extra):
    task = await task_service.create_task(
        db, user.id, TaskCreate(title=title, department="Financeiro", **extra)
    )
    await db.commit()
    return task


async def _index_row(db: AsyncSession, task_id: uuid.UUID):
    db.expire_all()
    return await db.scalar(
        select(TaskSearchIndex).where(TaskSearchIndex.task_id == task_id)
    )


async def test_other_user_task_never_retrieved(
    db_session: AsyncSession, user: User, other_user: User, embedder: FakeEmbedder
):
    mine = await _create(db_session, user, "Revisar relatório financeiro")
    theirs = await _create(db_session, other_user, "Revisar relatório financeiro")
    results = await task_retrieval.retrieve_related_tasks(
        db_session, user.id, "relatório financeiro"
    )
    ids = [r.task_id for r in results]
    assert mine.id in ids
    assert theirs.id not in ids
    assert results[0].origin == "both"


async def test_query_task_is_excluded(
    db_session: AsyncSession, user: User, embedder: FakeEmbedder
):
    task = await _create(db_session, user, "Revisar relatório financeiro")
    other = await _create(db_session, user, "Fechar relatório financeiro anual")
    results = await task_retrieval.retrieve_related_tasks(
        db_session, user.id, "relatório financeiro", exclude_task_id=task.id
    )
    assert [r.task_id for r in results] == [other.id]


async def test_statuses_filter(db_session: AsyncSession, user: User):
    open_task = await _create(db_session, user, "Deploy da API")
    done = await _create(db_session, user, "Deploy do front")
    await task_service.update_task(
        db_session, user.id, done.id, TaskUpdate(status=TaskStatus.completed)
    )
    await db_session.commit()
    results = await task_retrieval.retrieve_related_tasks(
        db_session, user.id, "deploy", statuses=[TaskStatus.completed]
    )
    assert [r.task_id for r in results] == [done.id]
    assert open_task.id not in [r.task_id for r in results]


async def test_update_reindexes_only_when_source_changes(
    db_session: AsyncSession, user: User, embedder: FakeEmbedder
):
    user_id = user.id
    task = await _create(db_session, user, "Revisar relatório")
    task_id = task.id
    first = await _index_row(db_session, task.id)
    old_hash = first.source_hash
    assert first.embedding_model == FAKE_MODEL and embedder.calls == 1

    await task_service.update_task(
        db_session, user_id, task_id, TaskUpdate(title="Corrigir deploy")
    )
    await db_session.commit()
    row = await _index_row(db_session, task_id)
    assert row.source_hash != old_hash
    assert "Corrigir deploy" in row.content
    assert embedder.calls == 2

    await task_service.update_task(
        db_session, user_id, task_id, TaskUpdate(title="Corrigir deploy")
    )
    await db_session.commit()
    assert embedder.calls == 2


async def test_delete_removes_index(
    async_client: AsyncClient, auth_headers: dict[str, str], db_session: AsyncSession
):
    created = await async_client.post(
        "/v1/tasks/", json={"title": "Temp", "department": "Ops"}, headers=auth_headers
    )
    task_id = uuid.UUID(created.json()["id"])
    assert await _index_row(db_session, task_id) is not None
    response = await async_client.delete(f"/v1/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 204
    assert await _index_row(db_session, task_id) is None


async def test_embedding_failure_on_index_keeps_task_and_lexical(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
    user: User,
    embedder: FakeEmbedder,
):
    user_id = user.id
    embedder.fail = True
    response = await async_client.post(
        "/v1/tasks/",
        json={"title": "Corrigir bug de login", "department": "Engenharia"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    task_id = uuid.UUID(response.json()["id"])
    row = await _index_row(db_session, task_id)
    assert row.embedding is None and row.embedding_model is None
    results = await task_retrieval.retrieve_related_tasks(db_session, user_id, "login")
    assert [(r.task_id, r.origin) for r in results] == [(task_id, "lexical")]


async def test_embedding_failure_on_search_keeps_lexical(
    db_session: AsyncSession, user: User, embedder: FakeEmbedder
):
    user_id = user.id
    task = await _create(db_session, user, "Proposta para cliente Acme")
    task_id = task.id
    assert (await _index_row(db_session, task_id)).embedding is not None
    embedder.fail = True
    results = await task_retrieval.retrieve_related_tasks(db_session, user_id, "acme")
    assert len(results) == 1
    assert results[0].task_id == task_id
    assert results[0].origin == "lexical"
    assert results[0].vector_score is None and results[0].lexical_score > 0


async def test_lexical_only_without_embedding_model(
    db_session: AsyncSession, user: User
):
    user_id = user.id
    task = await _create(db_session, user, "Migrar pipeline de deploy")
    task_id = task.id
    assert (await _index_row(db_session, task_id)).embedding is None
    results = await task_retrieval.retrieve_related_tasks(db_session, user_id, "deploy")
    assert [r.task_id for r in results] == [task_id]


def test_rrf_item_in_both_channels_ranks_first():
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    fused = task_retrieval.rrf_fuse([(a, 0.9), (b, 0.5)], [(c, 0.99), (b, 0.8)])
    assert fused[0].task_id == b
    assert fused[0].origin == "both"
    assert (fused[0].lexical_rank, fused[0].vector_rank) == (2, 2)
    assert fused[0].rrf_score == pytest.approx(2 / 62)
    assert {f.origin for f in fused[1:]} == {"lexical", "vector"}
