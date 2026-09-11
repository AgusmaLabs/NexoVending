"""API tests for pending product resolution (V11)."""

from __future__ import annotations

from tests.api.conftest import admin_headers, api, replenisher_headers


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


def test_post_line_pending_returns_null_product_id_and_pending_status(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "pend-create")
    rid = created["id"]
    response = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="pend-line"),
        json={
            "slot_id": api_world["slot_id"],
            "quantity": 3,
            "barcode": "9999999",
            "manual_description": "Bebida energética X",
        },
    )
    assert response.status_code == 200, response.text
    line = response.json()["lines"][0]
    assert line["product_id"] is None
    assert line["resolution_status"] == "pending_product_resolution"
    assert line["manual_description"] == "Bebida energética X"


def test_post_line_invalid_without_product_or_manual_returns_4xx(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "inv-create")
    rid = created["id"]
    response = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="inv-line"),
        json={"slot_id": api_world["slot_id"], "quantity": 1},
    )
    assert response.status_code in {400, 409, 422}


def test_barcode_404_then_pending_line_e2e_api_flow(api_world) -> None:
    client = api_world["client"]
    missing = client.get(
        api("/products/barcode/8888888"),
        headers=replenisher_headers(api_world),
    )
    assert missing.status_code == 404

    created = _create(client, api_world, "e2e-create")
    rid = created["id"]
    line = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="e2e-line"),
        json={
            "slot_id": api_world["slot_id"],
            "quantity": 2,
            "barcode": "8888888",
            "manual_description": "Unknown after 404",
        },
    )
    assert line.status_code == 200, line.text
    completed = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="e2e-complete"),
        json={},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["lines"][0]["resolution_status"] == "pending_product_resolution"


def test_get_pending_product_resolutions_admin_ok(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "list-create")
    rid = created["id"]
    client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="list-line"),
        json={
            "slot_id": api_world["slot_id"],
            "quantity": 1,
            "manual_description": "Queue me",
        },
    )
    response = client.get(
        api("/replenishments/pending-product-resolutions"),
        headers=admin_headers(api_world),
    )
    assert response.status_code == 200, response.text
    items = response.json()["items"]
    assert any(item["manual_description"] == "Queue me" for item in items)


def test_get_pending_product_resolutions_operator_forbidden(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        api("/replenishments/pending-product-resolutions"),
        headers=replenisher_headers(api_world),
    )
    assert response.status_code == 403


def test_post_resolve_product_admin_ok(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "res-create")
    rid = created["id"]
    lined = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="res-line"),
        json={
            "slot_id": api_world["slot_id"],
            "quantity": 2,
            "manual_description": "Resolve me",
        },
    ).json()
    line_id = lined["lines"][0]["id"]
    client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="res-complete"),
        json={},
    )
    resolved = client.post(
        api(f"/replenishments/{rid}/lines/{line_id}/resolve-product"),
        headers=admin_headers(api_world, key="res-resolve"),
        json={"product_id": api_world["product_id"]},
    )
    assert resolved.status_code == 200, resolved.text
    line = resolved.json()["lines"][0]
    assert line["resolution_status"] == "resolved"
    assert line["product_id"] == api_world["product_id"]
    assert line["resolved_by_operator_id"] == api_world["admin_id"]


def test_post_resolve_product_operator_forbidden(api_world) -> None:
    client = api_world["client"]
    created = _create(client, api_world, "forb-create")
    rid = created["id"]
    lined = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="forb-line"),
        json={
            "slot_id": api_world["slot_id"],
            "quantity": 1,
            "manual_description": "No",
        },
    ).json()
    line_id = lined["lines"][0]["id"]
    response = client.post(
        api(f"/replenishments/{rid}/lines/{line_id}/resolve-product"),
        headers=replenisher_headers(api_world, key="forb-resolve"),
        json={"product_id": api_world["product_id"]},
    )
    assert response.status_code == 403
