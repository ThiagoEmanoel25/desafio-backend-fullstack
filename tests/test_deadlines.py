"""Optional deadlines remain user-scoped and can be cleared."""


async def test_deadline_roundtrip_and_clear(async_client, auth_headers):
    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Entrega com prazo",
            "department": "Comercial",
            "due_date": "2026-12-15",
        },
    )
    assert response.status_code == 201
    task = response.json()
    assert task["due_date"] == "2026-12-15"
    response = await async_client.patch(
        f"/v1/tasks/{task['id']}", headers=auth_headers, json={"due_date": None}
    )
    assert response.status_code == 200
    assert response.json()["due_date"] is None


async def test_invalid_deadline(async_client, auth_headers):
    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Prazo inválido",
            "department": "Comercial",
            "due_date": "2026-02-30",
        },
    )
    assert response.status_code == 422
