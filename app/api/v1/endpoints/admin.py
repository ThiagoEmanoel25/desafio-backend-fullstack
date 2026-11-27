"""Administrator-only account management; task contents remain private."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter()


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Check privilege from the database, never from client claims."""
    if not user.is_admin:
        raise HTTPException(403, "Administrator access required")
    return user


class TenantResponse(UserResponse):
    is_active: bool


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    is_active: bool


@router.get("/tenants", response_model=list[TenantResponse])
async def list_tenants(
    limit: int = Query(50, ge=1, le=100),
    skip: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List account metadata with bounded pagination."""
    result = await db.scalars(
        select(User).order_by(User.created_at, User.id).offset(skip).limit(limit)
    )
    return result.all()


@router.patch("/tenants/{user_id}", response_model=TenantResponse)
async def update_tenant(
    user_id: uuid.UUID,
    payload: TenantUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate or deactivate an ordinary account without deleting its data."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "Account not found")
    if user.is_admin:
        raise HTTPException(409, "Administrator accounts cannot be changed here")
    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return user
