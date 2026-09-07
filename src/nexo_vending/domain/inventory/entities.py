from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.ids import InventoryMovementId, ProductId, UserId
from nexo_vending.domain.common.value_objects import Quantity, require_aware
from nexo_vending.domain.inventory.enums import InventoryMovementType


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    """Immutable stock ledger entry. Stock is derived, never mutated in place."""

    id: InventoryMovementId
    operator_id: UserId
    product_id: ProductId
    movement_type: InventoryMovementType
    quantity: Quantity
    reference: str
    created_at: datetime
    created_by: UserId

    def __post_init__(self) -> None:
        require_aware(self.created_at, field_name="created_at")
