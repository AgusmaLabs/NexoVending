"""HTTP ↔ application serialization helpers (no domain rules)."""

from __future__ import annotations

from typing import Any

from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.replenishment.entities import Replenishment


def location_to_dict(location: InventoryLocation | None) -> dict[str, str] | None:
    if location is None:
        return None
    payload: dict[str, str] = {
        "location_type": location.location_type.value,
        "holder_id": location.holder_id,
    }
    if location.position_id is not None:
        payload["position_id"] = location.position_id
    return payload


def replenishment_to_dict(replenishment: Replenishment) -> dict[str, Any]:
    return {
        "id": str(replenishment.id.value),
        "machine_id": str(replenishment.machine_id.value),
        "operator_id": str(replenishment.operator_id.value),
        "status": replenishment.status.value,
        "machine_type": replenishment.machine_type.value,
        "started_at": replenishment.started_at.isoformat(),
        "completed_at": (
            replenishment.completed_at.isoformat()
            if replenishment.completed_at is not None
            else None
        ),
        "location": {
            "latitude": replenishment.location.latitude,
            "longitude": replenishment.location.longitude,
            "accuracy": replenishment.location.accuracy,
        },
        "idempotency_key": replenishment.idempotency_key,
        "version": replenishment.version,
        "lines": [
            {
                "id": str(line.id.value),
                "slot_id": str(line.machine_position_id.value),
                "product_id": str(line.product_id.value),
                "quantity": line.quantity.value,
                "unit_price": str(line.unit_price),
                "occurred_at": line.occurred_at.isoformat(),
                "product_description_snapshot": line.product_description_snapshot,
                "preferred_product_id_snapshot": (
                    str(line.preferred_product_id_snapshot.value)
                    if line.preferred_product_id_snapshot is not None
                    else None
                ),
                "replacement_reason": (
                    line.replacement_reason.value
                    if line.replacement_reason is not None
                    else None
                ),
                "barcode_scanned": (
                    line.barcode_scanned.value if line.barcode_scanned is not None else None
                ),
                "manual_description": line.manual_description,
            }
            for line in replenishment.lines
        ],
    }


def movement_to_dict(movement: InventoryMovement) -> dict[str, Any]:
    return {
        "id": str(movement.id.value),
        "product_id": str(movement.product_id.value),
        "quantity": movement.quantity.value,
        "movement_type": movement.movement_type.value,
        "reference_type": movement.reference_type.value,
        "reference_id": movement.reference_id,
        "occurred_at": movement.occurred_at.isoformat(),
        "actor_id": str(movement.actor_id.value),
        "source_location": location_to_dict(movement.source_location),
        "destination_location": location_to_dict(movement.destination_location),
        "idempotency_key": movement.idempotency_key,
    }
