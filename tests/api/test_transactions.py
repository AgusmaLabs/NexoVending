"""Transactional rollback and concurrency via HTTP."""

from __future__ import annotations

from unittest.mock import patch

from tests.api.conftest import api, replenisher_headers


def test_complete_rollback_on_forced_failure(api_world) -> None:
    client = api_world["client"]
    created = client.post(
        api("/replenishments"),
        headers=replenisher_headers(api_world, key="rb-create"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    ).json()
    rid = created["id"]
    client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="rb-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 3,
        },
    )

    from nexo_vending.application.replenishment.complete import CompleteReplenishment

    real = CompleteReplenishment.execute

    async def boom(self, command):
        await real(self, command)
        raise RuntimeError("forced persistence failure")

    with patch.object(CompleteReplenishment, "execute", boom):
        response = client.post(
            api(f"/replenishments/{rid}/complete"),
            headers=replenisher_headers(api_world, key="rb-complete"),
            json={},
        )
    assert response.status_code == 500

    got = client.get(api(f"/replenishments/{rid}"), headers=replenisher_headers(api_world))
    assert got.status_code == 200
    assert got.json()["status"] == "IN_PROGRESS"


def test_concurrent_complete_respects_locking(api_world) -> None:
    client = api_world["client"]
    created = client.post(
        api("/replenishments"),
        headers=replenisher_headers(api_world, key="cc-create"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    ).json()
    rid = created["id"]
    client.post(
        api(f"/replenishments/{rid}/lines"),
        headers=replenisher_headers(api_world, key="cc-line"),
        json={
            "slot_id": api_world["slot_id"],
            "product_id": api_world["product_id"],
            "quantity": 2,
        },
    )

    first = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="cc-a"),
        json={},
    )
    second = client.post(
        api(f"/replenishments/{rid}/complete"),
        headers=replenisher_headers(api_world, key="cc-b"),
        json={},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    final = client.get(api(f"/replenishments/{rid}"), headers=replenisher_headers(api_world))
    assert final.json()["status"] == "COMPLETED"
