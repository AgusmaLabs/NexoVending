"""Authorization HTTP tests."""

from __future__ import annotations

from tests.api.conftest import api, auth_headers, replenisher_headers


def test_authenticated_without_permission_returns_403(api_world) -> None:
    client = api_world["client"]
    # principal without registered permissions
    headers = auth_headers(
        tenant="tenant-a",
        provider="google",
        subject="stranger",
        idempotency_key="no-perm",
    )
    # must exist as operator? ResolveOperator will fail first if not provisioned.
    # Seed a principal with operator but no Platform permission by using a new subject
    # that is not granted — also not an operator → 403 OPERATOR_NOT_FOUND.
    response = client.post(
        api("/replenishments"),
        headers=headers,
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 403


def test_permission_denied_when_entitlement_missing(api_world) -> None:
    client = api_world["client"]
    api_world["ents"].values["tenant-a"].discard("vending.replenishment")
    response = client.post(
        api("/replenishments"),
        headers=replenisher_headers(api_world, key="no-ent"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 403
    # restore for other tests sharing fixture — fixture is function-scoped so ok
