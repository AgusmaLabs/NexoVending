from __future__ import annotations

from collections.abc import Iterable

from nexo_vending.domain.common.errors import InsufficientStockError
from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType
from nexo_vending.domain.inventory.locations import InventoryLocation


class InventoryLedger:
    """Derives expected inventory from an immutable location-based movement history."""

    @staticmethod
    def signed_delta_for_location(
        movement: InventoryMovement,
        location: InventoryLocation,
    ) -> int:
        delta = 0
        if movement.destination_location == location:
            delta += movement.quantity.value
        if movement.source_location == location:
            delta -= movement.quantity.value
        return delta

    @classmethod
    def expected_quantity(
        cls,
        movements: Iterable[InventoryMovement],
        *,
        location: InventoryLocation,
        product_id: ProductId,
    ) -> int:
        total = 0
        for movement in movements:
            if movement.product_id != product_id:
                continue
            total += cls.signed_delta_for_location(movement, location)
        return total

    @classmethod
    def ensure_can_apply(
        cls,
        movements: Iterable[InventoryMovement],
        new_movement: InventoryMovement,
    ) -> None:
        """Reject movements that would drive any touched source location negative."""
        known = list(movements)
        if new_movement.source_location is not None:
            current = cls.expected_quantity(
                known,
                location=new_movement.source_location,
                product_id=new_movement.product_id,
            )
            if current - new_movement.quantity.value < 0:
                raise InsufficientStockError(
                    "inventory movement would result in negative stock at source"
                )

    @classmethod
    def is_loss(cls, movement: InventoryMovement) -> bool:
        return movement.movement_type == InventoryMovementType.LOSS

    @classmethod
    def is_slot_removal(cls, movement: InventoryMovement) -> bool:
        return movement.movement_type == InventoryMovementType.SLOT_REMOVAL
