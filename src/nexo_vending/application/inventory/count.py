from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import InventoryCountId, ProductId, UserId
from nexo_vending.domain.inventory.entities import InventoryCount, InventoryCountLine
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryCountRepository


@dataclass(frozen=True, slots=True)
class CreateInventoryCountCommand:
    location: InventoryLocation
    occurred_at: datetime
    actor_id: UserId


class CreateInventoryCount:
    def __init__(self, counts: InventoryCountRepository) -> None:
        self._counts = counts

    async def execute(self, command: CreateInventoryCountCommand) -> InventoryCount:
        count = InventoryCount.create(
            count_id=InventoryCountId.new(),
            location=command.location,
            occurred_at=command.occurred_at,
            actor_id=command.actor_id,
        )
        await self._counts.save(count)
        return count


@dataclass(frozen=True, slots=True)
class RecordInventoryCountLineCommand:
    count_id: InventoryCountId
    product_id: ProductId
    expected_quantity: int
    physical_quantity: int


class RecordInventoryCountLine:
    def __init__(self, counts: InventoryCountRepository) -> None:
        self._counts = counts

    async def execute(self, command: RecordInventoryCountLineCommand) -> InventoryCountLine:
        count = await self._counts.get(command.count_id)
        if count is None:
            raise DomainError("inventory count not found")
        line = count.record_line(
            product_id=command.product_id,
            expected_quantity=command.expected_quantity,
            physical_quantity=command.physical_quantity,
        )
        await self._counts.save(count)
        return line


@dataclass(frozen=True, slots=True)
class CompleteInventoryCountCommand:
    count_id: InventoryCountId


class CompleteInventoryCount:
    def __init__(self, counts: InventoryCountRepository) -> None:
        self._counts = counts

    async def execute(self, command: CompleteInventoryCountCommand) -> InventoryCount:
        count = await self._counts.get(command.count_id)
        if count is None:
            raise DomainError("inventory count not found")
        count.complete()
        await self._counts.save(count)
        return count
