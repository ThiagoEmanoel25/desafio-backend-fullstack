"""Reserve a daily slot before paid work; database failure blocks AI only."""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import Date, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_usage import AIUsage


async def reserve_ai(db: AsyncSession, user_id: UUID) -> None:
    """Atomically reserve global and user slots in an independent transaction.

    A failed or cancelled run keeps its slot: a provider may already have billed
    it. Fixed UTC days; authentication is required before calling this function.
    """
    if not (settings.AI_LIMITS_ENABLED or settings.APP_ENV == "production"):
        return
    try:
        async with AsyncSession(bind=db.bind) as quota_db, quota_db.begin():
            day = await quota_db.scalar(
                select(func.timezone("UTC", func.now()).cast(Date))
            )
            for scope, limit in (
                ("global", settings.AI_GLOBAL_DAILY_LIMIT),
                (f"user:{user_id}", settings.AI_USER_DAILY_LIMIT),
            ):
                statement = insert(AIUsage).values(scope=scope, day=day, used=1)
                statement = statement.on_conflict_do_update(
                    index_elements=[AIUsage.scope, AIUsage.day],
                    set_={"used": AIUsage.used + 1},
                    where=AIUsage.used < limit,
                ).returning(AIUsage.used)
                if await quota_db.scalar(statement) is None:
                    now = datetime.now(UTC)
                    tomorrow = (now + timedelta(days=1)).replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    raise HTTPException(
                        429,
                        "Limite diário de IA atingido. Tente novamente amanhã (UTC).",
                        headers={
                            "Retry-After": str(
                                max(1, int((tomorrow - now).total_seconds()))
                            )
                        },
                    )
    except SQLAlchemyError:
        raise HTTPException(
            503, "Não foi possível verificar a quota de IA. Tente novamente."
        ) from None
