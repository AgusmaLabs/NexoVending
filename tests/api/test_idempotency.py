"""HTTP idempotency tests using Platform IdempotencyService."""

from __future__ import annotations

from sqlalchemy import text

from tests.api.conftest import replenisher_headers


def test_complete_idempotency_key_does_not_duplicate_movements(api_world) -> None:
    client = api_world["client"]
    created = client.post(
        "/replenishments",
        headers=replenisher_headers(api_world, key="idem-create"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    ).json()
    rid = created["id"]
    client.post(
        f"/replenishments/{rid}/lines",
        headers=replenisher_headers(api_world, key="idem-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 4,
        },
    )

    headers = replenisher_headers(api_world, key="COMPLETE-ABC")
    first = client.post(f"/replenishments/{rid}/complete", headers=headers, json={})
    second = client.post(f"/replenishments/{rid}/complete", headers=headers, json={})
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert first.json()["status"] == "COMPLETED"

    session = api_world["session_factory"]()
    try:
        count = session.execute(
            text(
                "SELECT COUNT(*) FROM inventory_movements "
                "WHERE reference_id = :rid AND movement_type = 'REPLENISHMENT'"
            ),
            {"rid": rid},
        ).scalar_one()
        assert count == 1
    finally:
        session.close()
