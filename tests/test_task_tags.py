"""Colored tags follow the existing validation and owner-scoped CRUD."""

import pytest


async def test_tags_roundtrip_partial_update_and_clear(async_client, auth_headers):
    tags = [{"name": " Cliente ", "color": "#3366FF"}]
    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Entregar proposta",
            "department": "Comercial",
            "tags": tags,
        },
    )
    assert response.status_code == 201
    task = response.json()
    expected = [{"name": "Cliente", "color": "#3366FF"}]
    assert task["tags"] == expected
    path = f"/v1/tasks/{task['id']}"
    # Updating another field must not reset omitted tags.
    response = await async_client.patch(
        path, headers=auth_headers, json={"title": "Revisar proposta"}
    )
    assert response.json()["tags"] == expected
    response = await async_client.patch(
        path,
        headers=auth_headers,
        json={"tags": [{"name": "Revisão", "color": "#ffcc00"}]},
    )
    assert response.json()["tags"][0]["color"] == "#ffcc00"
    assert (await async_client.get("/v1/tasks/", headers=auth_headers)).json()[0][
        "tags"
    ] == response.json()["tags"]
    response = await async_client.patch(path, headers=auth_headers, json={"tags": []})
    assert response.status_code == 200
    assert response.json()["tags"] == []


@pytest.mark.parametrize(
    "tags",
    [
        [{"name": "Cliente", "color": "red"}],
        [{"name": "Cliente", "color": "url(javascript:alert(1))"}],
        [{"name": "   ", "color": "#ffffff"}],
        [{"name": "x" * 31, "color": "#ffffff"}],
        [{"name": "Tag", "color": "#ffffff"}] * 9,
        None,
    ],
)
async def test_invalid_tags_are_rejected(async_client, auth_headers, tags):
    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Entregar proposta",
            "department": "Comercial",
            "tags": tags,
        },
    )
    assert response.status_code == 422


async def test_other_user_cannot_read_or_change_tags(
    async_client, auth_headers, other_auth_headers
):
    response = await async_client.post(
        "/v1/tasks/",
        headers=auth_headers,
        json={
            "title": "Proposta privada",
            "department": "Comercial",
            "tags": [{"name": "Segredo", "color": "#000000"}],
        },
    )
    path = f"/v1/tasks/{response.json()['id']}"
    assert (await async_client.get(path, headers=other_auth_headers)).status_code == 404
    response = await async_client.patch(
        path, headers=other_auth_headers, json={"tags": []}
    )
    assert response.status_code == 404
    assert (await async_client.get(path, headers=auth_headers)).json()["tags"][0][
        "name"
    ] == "Segredo"
