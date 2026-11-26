"""
Shared Dependencies (Dependency Injection)
==========================================
FastAPI dependencies used across routes via `Depends(...)`.

`get_db()` yields the request's session; `get_current_user()` gates routes.
"""

import uuid
from collections.abc import AsyncGenerator

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_maker
from app.core.security import decode_access_token
from app.models.user import User
from app.repositories import user_repository

# Tells FastAPI/Swagger where the token comes from. Thanks to this, the
# "Authorize" button in Swagger UI (/docs) works with your login endpoint.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and close it at the end of the request."""
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Return the user the bearer token belongs to.

    Every failure (bad/expired token, bad `sub`, unknown or inactive user)
    raises the same 401 so callers cannot tell which one happened.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = uuid.UUID(decode_access_token(token)["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        raise unauthorized from None
    user = await user_repository.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise unauthorized
    return user
