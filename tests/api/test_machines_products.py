"""API tests for machine resolve and product barcode lookup."""

from __future__ import annotations

from tests.api.conftest import replenisher_headers


def test_resolve_machine_by_qr(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        "/machines/resolve",
        headers=replenisher_headers(api_world),
        params={"identifier_type": "QR_CODE", "value": "MIX-001"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["machine_id"] == api_world["machine_id"]
    assert body["identifier"] == "MIX-001"
    assert body["slots"]


def test_resolve_unknown_qr_404(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        "/machines/resolve",
        headers=replenisher_headers(api_world),
        params={"identifier_type": "QR_CODE", "value": "NOPE"},
    )
    assert response.status_code == 404


def test_tenant_isolation_machine(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        f"/machines/{api_world['machine_b_id']}",
        headers=replenisher_headers(api_world),
    )
    assert response.status_code in {403, 404}


def test_machine_slots(api_world) -> None:
    client = api_world["client"]
    response = client.get(
        f"/machines/{api_world['machine_id']}/slots",
        headers=replenisher_headers(api_world),
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["slots"]) == 1


def test_product_barcode_found_and_missing(api_world) -> None:
    client = api_world["client"]
    found = client.get(
        "/products/barcode/7800001",
        headers=replenisher_headers(api_world),
    )
    assert found.status_code == 200
    assert found.json()["barcode"] == "7800001"

    missing = client.get(
        "/products/barcode/9999999",
        headers=replenisher_headers(api_world),
    )
    assert missing.status_code == 404


def test_create_replenishment_accepts_accuracy_m(api_world) -> None:
    client = api_world["client"]
    response = client.post(
        "/replenishments",
        headers=replenisher_headers(api_world, key="acc-m"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {
                "latitude": -35.4264,
                "longitude": -71.6554,
                "accuracy_m": 12.4,
            },
        },
    )
    assert response.status_code == 201, response.text
