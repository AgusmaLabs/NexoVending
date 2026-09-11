"""Parse InventoryLocation HTTP payloads."""

from __future__ import annotations

from uuid import UUID

from nexo_vending.api.schemas.inventory import InventoryLocationIn
from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import MachineId, OperatorId, SlotId
from nexo_vending.domain.inventory.enums import InventoryLocationType
from nexo_vending.domain.inventory.locations import InventoryLocation


def parse_location(payload: InventoryLocationIn) -> InventoryLocation:
    try:
        location_type = InventoryLocationType(payload.location_type)
    except ValueError as exc:
        raise DomainError(f"invalid location_type: {payload.location_type}") from exc

    if location_type == InventoryLocationType.ADMINISTRATOR:
        return InventoryLocation.administrator(OperatorId(UUID(payload.holder_id)))
    if location_type == InventoryLocationType.REPLENISHER:
        return InventoryLocation.replenisher(OperatorId(UUID(payload.holder_id)))
    if location_type == InventoryLocationType.MACHINE_SLOT:
        if payload.position_id is None:
            raise DomainError("MACHINE_SLOT requires position_id")
        return InventoryLocation.machine_slot(
            MachineId(UUID(payload.holder_id)),
            SlotId(UUID(payload.position_id)),
        )
    if location_type == InventoryLocationType.MACHINE_CONTAINER:
        if payload.position_id is None:
            raise DomainError("MACHINE_CONTAINER requires position_id")
        return InventoryLocation.machine_container(
            MachineId(UUID(payload.holder_id)),
            SlotId(UUID(payload.position_id)),
        )
    raise DomainError(f"unsupported location_type: {payload.location_type}")
