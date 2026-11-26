"""
Test Configuration & Fixtures
==============================
Strategy: a separate Postgres database (`TEST_DATABASE_URL`) whose tables are
created once per session with `Base.metadata.create_all` and dropped at the
end. Every test gets a fresh `AsyncSession` that `get_db` is overridden to
return, and all tables are truncated after each test so rows never leak.

Real LLM calls are blocked for the whole suite; override the agent's model
with PydanticAI's `TestModel` / `FunctionModel` instead.
"""

import asyncio
from collections.abc import AsyncGenerator, Iterator

import pytest
from httpx import ASGITransport, AsyncClient
from pydantic_ai import models
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.config import settings
from app.main import app
from app.models import Base

models.ALLOW_MODEL_REQUESTS = False


def _test_database_url() -> str:
    if not settings.TEST_DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL is not set. Point it at a separate Postgres "
            "database (e.g. run `source .dev-env.sh`).",
            returncode=2,
        )
    return settings.TEST_DATABASE_URL


@pytest.fixture(autouse=True)
def _block_real_llm_calls() -> Iterator[None]:
    """Fail loudly if a test forgets to override the model (no network)."""
    previous = models.ALLOW_MODEL_REQUESTS
    models.ALLOW_MODEL_REQUESTS = False
    yield
    models.ALLOW_MODEL_REQUESTS = previous


@pytest.fixture(scope="session", autouse=True)
def _test_schema() -> Iterator[None]:
    """Create all tables before the suite and drop them after it."""
    url = _test_database_url()

    async def run(drop: bool) -> None:
        engine = create_async_engine(url, poolclass=NullPool)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            if not drop:
                await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(run(drop=False))
    yield
    asyncio.run(run(drop=True))


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Session on the test database; all tables are truncated after the test."""
    # ponytail: engine per test (NullPool) because the loop is function-scoped.
    engine = create_async_engine(_test_database_url(), poolclass=NullPool)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()
        tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
        await session.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
        await session.commit()
    await engine.dispose()


@pytest.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client that calls the FastAPI app in-process, using `db_session`."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
