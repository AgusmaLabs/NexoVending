"""List inventory movements for a location (tenant-scoped)."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository


@dataclass(frozen=True, slots=True)
class ListInventoryMovementsQuery:
    tenant_id: TenantId
    location: InventoryLocation
    product_id: ProductId | None = None


class ListInventoryMovements:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._inventory = inventory

    async def execute(self, query: ListInventoryMovementsQuery) -> list[InventoryMovement]:
        movements = await self._inventory.list_movements_for_location(
            query.location,
            query.product_id,
        )
        return [m for m in movements if m.tenant_id == query.tenant_id]
