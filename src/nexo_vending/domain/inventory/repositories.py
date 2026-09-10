from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import InventoryCountId, ProductId, TenantId
from nexo_vending.domain.inventory.entities import InventoryCount, InventoryMovement
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.periods import MachineInventoryPeriod


class InventoryRepository(Protocol):
    async def record_movement(self, movement: InventoryMovement) -> None: ...

    async def find_by_idempotency_key(
        self,
        tenant_id: TenantId,
        idempotency_key: str,
    ) -> InventoryMovement | None: ...

    async def list_movements_for_location(
        self,
        location: InventoryLocation,
        product_id: ProductId | None = None,
    ) -> list[InventoryMovement]: ...

    async def expected_quantity(
        self,
        location: InventoryLocation,
        product_id: ProductId,
    ) -> int: ...


class InventoryCountRepository(Protocol):
    async def get(self, count_id: InventoryCountId) -> InventoryCount | None: ...

    async def save(self, count: InventoryCount) -> None: ...


class MachineInventoryPeriodRepository(Protocol):
    async def get_open(
        self,
        machine_id,
        position_id,
    ) -> MachineInventoryPeriod | None: ...

    async def save(self, period: MachineInventoryPeriod) -> None: ...
