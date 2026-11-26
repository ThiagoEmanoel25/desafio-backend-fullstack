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
from app.core.security import create_access_token, hash_password
from app.main import app
from app.models import Base
from app.models.user import User

# Long enough to silence PyJWT's HMAC key-length warning.
settings.JWT_SECRET_KEY = "test-secret-key-at-least-32-bytes-long"


def _test_database_url() -> str:
    if not settings.TEST_DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL is not set. Point it at a separate Postgres "
            "database (e.g. run `source .dev-env.sh`).",
            returncode=2,
        )
    if settings.TEST_DATABASE_URL == settings.DATABASE_URL:
        pytest.exit(
            "TEST_DATABASE_URL equals DATABASE_URL; the suite drops tables.",
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


PASSWORD = "correct-horse-battery"


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(
        email=email, full_name="Test User", hashed_password=hash_password(PASSWORD)
    )
    db.add(user)
    await db.commit()
    return user


@pytest.fixture
async def user(db_session: AsyncSession) -> User:
    """An active user; log in with `PASSWORD`."""
    return await _make_user(db_session, "user@example.com")


@pytest.fixture
async def other_user(db_session: AsyncSession) -> User:
    """A second active user, for isolation tests."""
    return await _make_user(db_session, "other@example.com")


@pytest.fixture
def auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


@pytest.fixture
def other_auth_headers(other_user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(other_user.id))}"}
