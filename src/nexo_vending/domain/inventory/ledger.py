from __future__ import annotations

from collections.abc import Iterable

from nexo_vending.domain.common.errors import InsufficientStockError
from nexo_vending.domain.common.ids import ProductId, UserId
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType

_INCREASE = {
    InventoryMovementType.ASSIGNMENT,
    InventoryMovementType.RETURN,
    InventoryMovementType.ADJUSTMENT,
}
_DECREASE = {
    InventoryMovementType.REPLENISHMENT,
    InventoryMovementType.LOSS,
}


class InventoryLedger:
    """Derives operator/product stock from an immutable movement history."""

    @staticmethod
    def signed_delta(movement: InventoryMovement) -> int:
        amount = movement.quantity.value
        if movement.movement_type in _INCREASE:
            return amount
        if movement.movement_type in _DECREASE:
            return -amount
        raise ValueError(f"unsupported movement type: {movement.movement_type}")

    @classmethod
    def stock_for(
        cls,
        movements: Iterable[InventoryMovement],
        *,
        operator_id: UserId,
        product_id: ProductId,
    ) -> int:
        total = 0
        for movement in movements:
            if movement.operator_id != operator_id or movement.product_id != product_id:
                continue
            total += cls.signed_delta(movement)
        return total

    @classmethod
    def ensure_can_apply(
        cls,
        movements: Iterable[InventoryMovement],
        new_movement: InventoryMovement,
    ) -> int:
        """Return resulting stock or raise if the movement would go negative."""
        current = cls.stock_for(
            movements,
            operator_id=new_movement.operator_id,
            product_id=new_movement.product_id,
        )
        resulting = current + cls.signed_delta(new_movement)
        if resulting < 0:
            raise InsufficientStockError(
                "inventory movement would result in negative stock"
            )
        return resulting
