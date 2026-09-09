from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from nexo_vending.domain.common.ids import MachineId, OperatorId, SlotId
from nexo_vending.domain.inventory.enums import InventoryLocationType


@dataclass(frozen=True, slots=True)
class InventoryLocation:
    """Where product physically sits (custody or machine position)."""

    location_type: InventoryLocationType
    holder_id: str
    position_id: str | None = None

    def __post_init__(self) -> None:
        holder = self.holder_id.strip()
        if not holder:
            raise ValueError("holder_id is required")
        position = self.position_id.strip() if self.position_id else None
        if position == "":
            position = None
        if self.location_type in (
            InventoryLocationType.MACHINE_SLOT,
            InventoryLocationType.MACHINE_CONTAINER,
        ):
            if position is None:
                raise ValueError("machine locations require position_id")
        elif position is not None:
            raise ValueError("person custody locations must not set position_id")
        object.__setattr__(self, "holder_id", holder)
        object.__setattr__(self, "position_id", position)

    @classmethod
    def administrator(cls, operator_id: OperatorId | UUID | str) -> InventoryLocation:
        return cls(
            location_type=InventoryLocationType.ADMINISTRATOR,
            holder_id=str(getattr(operator_id, "value", operator_id)),
        )

    @classmethod
    def replenisher(cls, operator_id: OperatorId | UUID | str) -> InventoryLocation:
        return cls(
            location_type=InventoryLocationType.REPLENISHER,
            holder_id=str(getattr(operator_id, "value", operator_id)),
        )

    @classmethod
    def machine_slot(
        cls,
        machine_id: MachineId | UUID | str,
        slot_id: SlotId | UUID | str,
    ) -> InventoryLocation:
        return cls(
            location_type=InventoryLocationType.MACHINE_SLOT,
            holder_id=str(getattr(machine_id, "value", machine_id)),
            position_id=str(getattr(slot_id, "value", slot_id)),
        )

    @classmethod
    def machine_container(
        cls,
        machine_id: MachineId | UUID | str,
        container_id: SlotId | UUID | str,
    ) -> InventoryLocation:
        return cls(
            location_type=InventoryLocationType.MACHINE_CONTAINER,
            holder_id=str(getattr(machine_id, "value", machine_id)),
            position_id=str(getattr(container_id, "value", container_id)),
        )
