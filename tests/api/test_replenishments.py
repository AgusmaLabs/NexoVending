"""Replenishment HTTP flow tests."""

from __future__ import annotations

from tests.api.conftest import api, replenisher_headers


def _create(client, world, key: str) -> dict:
    response = client.post(
        api("/replenishments"),
        headers=replenisher_headers(world, key=key),
        json={
            "machine_id": world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_get_add_line_complete_cancel_flow(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "flow-create")
    rid = created["id"]

    got = client.get(api(f"/replenishments/{rid}"), headers=replenisher_headers(api_world))
    assert got.status_code == 200
    assert got.json()["id"] == rid

    line = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="flow-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 5,
        },
    )
    assert line.status_code == 200, line.text
    assert len(line.json()["lines"]) == 1

    completed = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="flow-complete"),
        json={},
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"


def test_cancel_replenishment(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "cancel-create")
    rid = created["id"]
    cancelled = client.post(
        api(f"/replenishments/{rid}/cancel"),
        headers=replenisher_headers(api_world, key="cancel-1"),
        json={},
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"


def test_unknown_replenishment_returns_404(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        api("/replenishments/00000000-0000-0000-0000-000000000099"),
        headers=replenisher_headers(api_world),
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "NOT_FOUND"
    assert body["error"]["request_id"]


def test_invalid_state_complete_twice_is_idempotent_at_domain(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "twice-create")
    rid = created["id"]
    client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="twice-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 2,
        },
    )
    first = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="twice-c1"),
        json={},
    )
    assert first.status_code == 200
    second = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="twice-c2"),
        json={},
    )
    assert second.status_code == 200
    assert second.json()["status"] == "COMPLETED"


def test_capacity_exceeded_returns_409(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "cap-create")
    rid = created["id"]
    response = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="cap-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 11,
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] in {"CAPACITY_EXCEEDED", "DOMAIN_ERROR"}
