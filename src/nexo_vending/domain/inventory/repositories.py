from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import ProductId, UserId
from nexo_vending.domain.inventory.entities import InventoryMovement


class InventoryRepository(Protocol):
    async def get_stock(self, operator_id: UserId, product_id: ProductId) -> int: ...

    async def record_movement(self, movement: InventoryMovement) -> None: ...

    async def list_movements(
        self,
        operator_id: UserId,
        product_id: ProductId,
    ) -> list[InventoryMovement]: ...
