"""Inventory HTTP tests."""

from __future__ import annotations

from tests.api.conftest import admin_headers


def test_assign_balance_and_movements(api_world) -> None:
    client = api_world["client"]
    assign = client.post(
        "/inventory/assignments",
        headers=admin_headers(api_world, key="inv-assign-1"),
        json={
            "product_id": api_world["product_id"],
            "quantity": 3,
            "replenisher_id": api_world["replenisher_id"],
            "reference_id": "assign-http-1",
        },
    )
    assert assign.status_code == 201, assign.text

    balance = client.get(
        "/inventory/balance",
        headers=admin_headers(api_world),
        params={
            "location_type": "REPLENISHER",
            "holder_id": api_world["replenisher_id"],
            "product_id": api_world["product_id"],
        },
    )
    assert balance.status_code == 200, balance.text
    assert balance.json()["quantity"] >= 53

    movements = client.get(
        "/inventory/movements",
        headers=admin_headers(api_world),
        params={
            "location_type": "REPLENISHER",
            "holder_id": api_world["replenisher_id"],
            "product_id": api_world["product_id"],
        },
    )
    assert movements.status_code == 200
    assert len(movements.json()["items"]) >= 2


def test_adjust_and_loss(api_world) -> None:
    client = api_world["client"]
    adjust = client.post(
        "/inventory/adjustments",
        headers=admin_headers(api_world, key="inv-adj-1"),
        json={
            "product_id": api_world["product_id"],
            "quantity": 1,
            "location": {
                "location_type": "REPLENISHER",
                "holder_id": api_world["replenisher_id"],
            },
            "reference_id": "adj-1",
            "as_increase": True,
        },
    )
    assert adjust.status_code == 201, adjust.text

    loss = client.post(
        "/inventory/losses",
        headers=admin_headers(api_world, key="inv-loss-1"),
        json={
            "product_id": api_world["product_id"],
            "quantity": 1,
            "location": {
                "location_type": "REPLENISHER",
                "holder_id": api_world["replenisher_id"],
            },
            "reference_id": "loss-1",
        },
    )
    assert loss.status_code == 201, loss.text
