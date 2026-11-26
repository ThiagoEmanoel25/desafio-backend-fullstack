"""User repository (data access layer).

Convention shared with the other repositories: methods only query and
`flush()`; they never `commit()`. The caller (route or service) owns the
transaction, so one request is one commit and a failure rolls everything back.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_email(db: AsyncSession, email: str) -> User | None:
    """Return the user with this e-mail, or None."""
    return await db.scalar(select(User).where(User.email == email))


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    """Return the user with this id, or None."""
    return await db.get(User, user_id)


async def create(db: AsyncSession, user: User) -> User:
    """Add the user and flush so its defaults are populated (no commit)."""
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
