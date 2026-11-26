"""Best-effort Redis cache. Postgres is always the source of truth.

Every helper swallows Redis errors (connection, timeout, bad payload): it logs a
`cache_degraded` line and behaves like a cache miss, so Redis being down never
takes the API down. Keys always start with the authenticated `user_id`.
"""

import hashlib
import json
import logging
import random
import uuid

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

_client: Redis | None = None


def get_redis() -> Redis | None:
    """Return the shared Redis client, or None when `REDIS_URL` is empty."""
    global _client
    if _client is None and settings.REDIS_URL:
        _client = Redis.from_url(
            settings.REDIS_URL,
            socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
            socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
            decode_responses=True,
        )
    return _client


def _degraded(operation: str, exc: Exception) -> None:
    logger.warning(
        "cache_degraded",
        extra={"operation": operation, "error_type": type(exc).__name__},
    )


def ttl_with_jitter(ttl: int) -> int:
    """Spread expirations by up to 10% so keys do not all expire together."""
    return ttl + random.randint(0, max(1, ttl // 10))


async def get_value(key: str) -> str | None:
    """Return the cached value, or None on miss, when disabled or on failure."""
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(key)
    except Exception as exc:
        _degraded("get", exc)
        return None


async def set_value(key: str, value: str, ttl: int) -> None:
    """Store `value` with a jittered TTL; failures are logged and ignored."""
    client = get_redis()
    if client is None:
        return
    try:
        await client.set(key, value, ex=ttl_with_jitter(ttl))
    except Exception as exc:
        _degraded("set", exc)


def _version_key(user_id: uuid.UUID) -> str:
    return f"tasks:version:{user_id}"


async def task_list_version(user_id: uuid.UUID) -> str | None:
    """The user's task list version (bumped on every task write); None if down."""
    client = get_redis()
    if client is None:
        return None
    try:
        return await client.get(_version_key(user_id)) or "0"
    except Exception as exc:
        _degraded("get_version", exc)
        return None


async def task_list_key(user_id: uuid.UUID, **filters: object) -> str | None:
    """Build `tasks:list:{user_id}:{version}:{filters_hash}`; None if unavailable."""
    version = await task_list_version(user_id)
    if version is None:
        return None
    raw = json.dumps(filters, sort_keys=True, default=str)
    filters_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"tasks:list:{user_id}:{version}:{filters_hash}"


async def bump_task_list_version(user_id: uuid.UUID) -> None:
    """Invalidate every cached list of the user by moving to a new version."""
    client = get_redis()
    if client is None:
        return
    try:
        await client.incr(_version_key(user_id))
    except Exception as exc:
        _degraded("bump_version", exc)
