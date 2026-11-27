"""Administrative access never follows from ordinary registration."""


async def test_registration_cannot_grant_admin(async_client):
    response = await async_client.post(
        "/v1/auth/register",
        json={
            "email": "attacker@example.com",
            "full_name": "Ordinary User",
            "password": "password123",
            "is_admin": True,
        },
    )
    assert response.status_code == 201
    assert response.json()["is_admin"] is False


async def test_admin_requires_privilege(async_client, auth_headers):
    assert (await async_client.get("/v1/admin/tenants")).status_code == 401
    assert (
        await async_client.get("/v1/admin/tenants", headers=auth_headers)
    ).status_code == 403


async def test_admin_can_disable_tenant(
    async_client, db_session, user, other_user, auth_headers, other_auth_headers
):
    user.is_admin = True
    await db_session.commit()
    result = await async_client.get("/v1/admin/tenants", headers=auth_headers)
    assert result.status_code == 200
    assert "hashed_password" not in result.text
    response = await async_client.patch(
        f"/v1/admin/tenants/{other_user.id}",
        json={"is_active": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert (
        await async_client.get("/v1/auth/me", headers=other_auth_headers)
    ).status_code == 401
    assert (
        await async_client.patch(
            f"/v1/admin/tenants/{user.id}",
            json={"is_active": False},
            headers=auth_headers,
        )
    ).status_code == 409
