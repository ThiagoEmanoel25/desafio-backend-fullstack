"""Authentication tests."""

from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import create_access_token
from app.models.user import User
from tests.conftest import PASSWORD

REGISTER = {
    "email": "new@example.com",
    "full_name": "New User",
    "password": "supersecret1",
}


async def test_register_success(async_client: AsyncClient) -> None:
    response = await async_client.post("/v1/auth/register", json=REGISTER)
    assert response.status_code == 201
    body = response.json()
    assert set(body) == {"id", "email", "full_name", "created_at", "is_admin"}
    assert body["is_admin"] is False
    assert body["email"] == REGISTER["email"]


async def test_register_duplicated_email(async_client: AsyncClient) -> None:
    await async_client.post("/v1/auth/register", json=REGISTER)
    response = await async_client.post("/v1/auth/register", json=REGISTER)
    assert response.status_code == 409


async def test_login_success(async_client: AsyncClient, user: User) -> None:
    response = await async_client.post(
        "/v1/auth/login", data={"username": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    me = await async_client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == user.email


async def test_login_invalid_password(async_client: AsyncClient, user: User) -> None:
    response = await async_client.post(
        "/v1/auth/login", data={"username": user.email, "password": "wrong-password"}
    )
    assert response.status_code == 401


async def test_login_unknown_email(async_client: AsyncClient, user: User) -> None:
    wrong_password = await async_client.post(
        "/v1/auth/login", data={"username": user.email, "password": "wrong-password"}
    )
    unknown = await async_client.post(
        "/v1/auth/login", data={"username": "nobody@example.com", "password": PASSWORD}
    )
    assert unknown.status_code == 401
    assert unknown.json() == wrong_password.json()


async def test_me_returns_current_user(
    async_client: AsyncClient, user: User, auth_headers: dict[str, str]
) -> None:
    response = await async_client.get("/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(user.id)
    assert "hashed_password" not in response.json()


async def test_protected_route_without_token(async_client: AsyncClient) -> None:
    response = await async_client.get("/v1/auth/me")
    assert response.status_code == 401


async def test_protected_route_with_invalid_token(async_client: AsyncClient) -> None:
    response = await async_client.get(
        "/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )
    assert response.status_code == 401


async def test_protected_route_with_expired_token(
    async_client: AsyncClient, user: User
) -> None:
    with patch.object(settings, "JWT_EXPIRATION_MINUTES", -5):
        token = create_access_token(str(user.id))
    response = await async_client.get(
        "/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 401


async def test_inactive_user_is_rejected(
    async_client: AsyncClient,
    db_session: AsyncSession,
    user: User,
    auth_headers: dict[str, str],
) -> None:
    user.is_active = False
    await db_session.commit()
    response = await async_client.get("/v1/auth/me", headers=auth_headers)
    assert response.status_code == 401
