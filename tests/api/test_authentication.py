"""Authentication HTTP tests."""

from __future__ import annotations

from tests.api.conftest import api, replenisher_headers


def test_missing_credentials_returns_401(api_world) -> None:
    client = api_world["client"]
    response = client.get(api(f"/replenishments/{api_world['machine_id']}"))
    assert response.status_code == 401


def test_missing_tenant_header_returns_401(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        api(f"/replenishments/{api_world['machine_id']}"),
        headers={"Authorization": "Bearer principal/google/replenisher-1"},
    )
    assert response.status_code == 401


def test_valid_principal_reaches_handler(api_world) -> None:
    client = api_world["client"]
    response = client.post(
        api("/replenishments"),
        headers=replenisher_headers(api_world, key="auth-create-1"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 201
    assert response.json()["status"] == "IN_PROGRESS"
