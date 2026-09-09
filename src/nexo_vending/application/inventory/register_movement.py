from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    ProductId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository


@dataclass(frozen=True, slots=True)
class RegisterInventoryMovementCommand:
    product_id: ProductId
    quantity: int
    movement_type: InventoryMovementType
    reference_type: InventoryReferenceType
    reference_id: str
    occurred_at: datetime
    actor_id: UserId
    source_location: InventoryLocation | None = None
    destination_location: InventoryLocation | None = None


class RegisterInventoryMovement:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._inventory = inventory

    async def execute(self, command: RegisterInventoryMovementCommand) -> InventoryMovement:
        movement = InventoryMovement(
            id=InventoryMovementId.new(),
            product_id=command.product_id,
            quantity=Quantity(command.quantity),
            movement_type=command.movement_type,
            reference_type=command.reference_type,
            reference_id=command.reference_id,
            occurred_at=command.occurred_at,
            actor_id=command.actor_id,
            source_location=command.source_location,
            destination_location=command.destination_location,
        )
        await self._inventory.record_movement(movement)
        return movement
