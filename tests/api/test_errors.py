"""Tenant isolation via HTTP."""

from __future__ import annotations

from tests.api.conftest import api, auth_headers, replenisher_headers


def test_tenant_a_cannot_read_tenant_b_replenishment(api_world) -> None:
    client = api_world["client"]
    # Create replenishment as tenant B
    created = client.post(
        api("/replenishments"),
        headers=auth_headers(
            tenant="tenant-b",
            provider="google",
            subject=api_world["tenant_b_subject"],
            idempotency_key="tb-create",
        ),
        json={
            "machine_id": api_world["machine_b_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert created.status_code == 201, created.text
    rid = created.json()["id"]

    denied = client.get(
        api(f"/replenishments/{rid}"),
        headers=replenisher_headers(api_world),
    )
    assert denied.status_code == 404

    line = client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="cross-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 1,
        },
    )
    # get finds wrong tenant → not found OR machine mismatch
    assert line.status_code in {404, 409}
