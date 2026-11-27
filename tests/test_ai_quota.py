"""Quota reservations survive failed work and are safe across concurrent requests."""

import asyncio
import uuid
from datetime import date

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from app.agent.agent import agent
from app.config import settings
from app.core import ai_quota
from app.models.ai_usage import AIUsage


async def test_assistance_cache_does_not_consume_another_slot(
    async_client, auth_headers, db_session, quotas
):
    from pydantic_ai.models.test import TestModel

    from app.agent.task_assistant import task_assistant

    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Analisar números",
            "department": "Fin",
            "description": "Conferir as entradas e saídas do mês.",
        },
    )
    path = f"/v1/tasks/{response.json()['id']}/assist"
    with task_assistant.override(model=TestModel()):
        assert (await async_client.post(path, headers=auth_headers)).status_code == 200
        assert (await async_client.post(path, headers=auth_headers)).status_code == 200
    assert (
        await db_session.scalar(select(AIUsage.used).where(AIUsage.scope == "global"))
        == 1
    )


@pytest.fixture
def quotas(monkeypatch):
    monkeypatch.setattr(settings, "AI_LIMITS_ENABLED", True)
    monkeypatch.setattr(settings, "AI_USER_DAILY_LIMIT", 2)
    monkeypatch.setattr(settings, "AI_GLOBAL_DAILY_LIMIT", 3)


async def test_user_limit_rolls_back_global_reservation(db_session, quotas):
    user = uuid.uuid4()
    await ai_quota.reserve_ai(db_session, user)
    await ai_quota.reserve_ai(db_session, user)
    with pytest.raises(HTTPException) as error:
        await ai_quota.reserve_ai(db_session, user)
    assert error.value.status_code == 429
    assert int(error.value.headers["Retry-After"]) > 0
    # Rejection of this user must not consume the last global slot.
    await ai_quota.reserve_ai(db_session, uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        await ai_quota.reserve_ai(db_session, uuid.uuid4())
    assert error.value.status_code == 429
    assert (
        await db_session.scalar(select(AIUsage.used).where(AIUsage.scope == "global"))
        == 3
    )


async def test_concurrent_reservations_never_exceed_global_limit(db_session, quotas):
    async def reserve():
        try:
            await ai_quota.reserve_ai(db_session, uuid.uuid4())
            return True
        except HTTPException as exc:
            assert exc.status_code == 429
            return False

    assert sum(await asyncio.gather(*(reserve() for _ in range(12)))) == 3


async def test_previous_day_does_not_block_today(db_session, quotas):
    db_session.add(AIUsage(scope="global", day=date(2000, 1, 1), used=3))
    await db_session.commit()
    await ai_quota.reserve_ai(db_session, uuid.uuid4())


async def test_database_failure_blocks_ai(db_session, quotas, monkeypatch):
    class BrokenSession:
        async def __aenter__(self):
            raise OperationalError("connect", {}, RuntimeError("offline"))

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(ai_quota, "AsyncSession", lambda **kw: BrokenSession())
    with pytest.raises(HTTPException) as error:
        await ai_quota.reserve_ai(db_session, uuid.uuid4())
    assert error.value.status_code == 503


async def test_both_chat_routes_reject_before_model_or_stream(
    async_client, db_session, user, auth_headers, quotas, monkeypatch
):
    await ai_quota.reserve_ai(db_session, user.id)
    await ai_quota.reserve_ai(db_session, user.id)
    calls = []

    async def unexpected(*args, **kwargs):
        calls.append(True)
        raise AssertionError("Must not invoke the model")

    monkeypatch.setattr(agent, "run", unexpected)
    monkeypatch.setattr(agent, "run_stream_events", unexpected)
    for path in ("/v1/chat", "/v1/chat/stream"):
        response = await async_client.post(
            path, headers=auth_headers, json={"message": "Crie uma tarefa"}
        )
        assert response.status_code == 429
        assert "Retry-After" in response.headers
    assert calls == []
    assert (
        await async_client.get("/v1/tasks/", headers=auth_headers)
    ).status_code == 200


async def test_production_enforces_quota_even_when_local_flag_disabled(
    db_session, monkeypatch
):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "AI_LIMITS_ENABLED", False)
    monkeypatch.setattr(settings, "AI_GLOBAL_DAILY_LIMIT", 1)
    await ai_quota.reserve_ai(db_session, uuid.uuid4())
    with pytest.raises(HTTPException) as error:
        await ai_quota.reserve_ai(db_session, uuid.uuid4())
    assert error.value.status_code == 429
