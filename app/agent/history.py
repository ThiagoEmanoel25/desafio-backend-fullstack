"""Chat history in Redis only: `chat:{user_id}:{conversation_id}`.

The user_id comes from the JWT, so another user's conversation_id simply misses
and starts a new conversation. Redis failures (see `app.core.cache`) degrade to
an empty history. Messages never go to Postgres.
"""

import logging
import uuid

from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    UserPromptPart,
)

from app.config import settings
from app.core import cache

logger = logging.getLogger(__name__)


def history_key(user_id: uuid.UUID, conversation_id: uuid.UUID) -> str:
    return f"chat:{user_id}:{conversation_id}"


def _starts_turn(message: ModelMessage) -> bool:
    return isinstance(message, ModelRequest) and any(
        isinstance(p, UserPromptPart) for p in message.parts
    )


def trim(messages: list[ModelMessage], limit: int) -> list[ModelMessage]:
    """Keep at most `limit` recent messages, starting on a user turn.

    Cutting only at a user prompt never leaves a tool return without its call.
    """
    tail = messages[-limit:] if limit > 0 else []
    for i, message in enumerate(tail):
        if _starts_turn(message):
            return tail[i:]
    return []


async def load(user_id: uuid.UUID, conversation_id: uuid.UUID) -> list[ModelMessage]:
    raw = await cache.get_value(history_key(user_id, conversation_id))
    if raw is None:
        return []
    try:
        messages = ModelMessagesTypeAdapter.validate_json(raw)
    except ValueError:
        logger.warning("cache_degraded", extra={"operation": "decode_chat_history"})
        return []
    return trim(messages, settings.CHAT_HISTORY_MAX_MESSAGES)


async def save(
    user_id: uuid.UUID, conversation_id: uuid.UUID, messages: list[ModelMessage]
) -> None:
    kept = trim(messages, settings.CHAT_HISTORY_MAX_MESSAGES)
    await cache.set_value(
        history_key(user_id, conversation_id),
        ModelMessagesTypeAdapter.dump_json(kept).decode(),
        settings.CHAT_HISTORY_TTL_SECONDS,
    )
