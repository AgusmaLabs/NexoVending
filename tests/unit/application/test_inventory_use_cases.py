from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from nexo_vending.application.inventory.count import (
    CompleteInventoryCount,
    CompleteInventoryCountCommand,
    CreateInventoryCount,
    CreateInventoryCountCommand,
    RecordInventoryCountLine,
    RecordInventoryCountLineCommand,
)
from nexo_vending.application.inventory.register_movement import (
    RegisterInventoryMovement,
    RegisterInventoryMovementCommand,
)
from nexo_vending.domain.common.ids import ProductId, TenantId, UserId
from nexo_vending.domain.inventory.enums import (
    InventoryCountStatus,
    InventoryMovementType,
    InventoryReferenceType,
)
from nexo_vending.domain.inventory.locations import InventoryLocation
from tests.support.fakes import InMemoryInventoryCountRepository, InMemoryInventoryRepository


def test_register_movement_and_count_without_auto_loss() -> None:
    asyncio.run(_test_register_movement_and_count_without_auto_loss())


async def _test_register_movement_and_count_without_auto_loss() -> None:
    inventory = InMemoryInventoryRepository()
    counts = InMemoryInventoryCountRepository()
    admin = UserId.new()
    product = ProductId.new()
    location = InventoryLocation.administrator(admin)

    await RegisterInventoryMovement(inventory).execute(
        RegisterInventoryMovementCommand(
            tenant_id=TenantId("tenant-a"),
            product_id=product,
            quantity=10,
            movement_type=InventoryMovementType.ADJUSTMENT,
            reference_type=InventoryReferenceType.PURCHASE,
            reference_id="purchase-1",
            occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
            actor_id=admin,
            destination_location=location,
        )
    )
    assert await inventory.expected_quantity(location, product) == 10

    count = await CreateInventoryCount(counts).execute(
        CreateInventoryCountCommand(
            location=location,
            occurred_at=datetime(2026, 9, 8, tzinfo=UTC),
            actor_id=admin,
        )
    )
    line = await RecordInventoryCountLine(counts).execute(
        RecordInventoryCountLineCommand(
            count_id=count.id,
            product_id=product,
            expected_quantity=10,
            physical_quantity=9,
        )
    )
    assert line.variance == -1
    completed = await CompleteInventoryCount(counts).execute(
        CompleteInventoryCountCommand(count_id=count.id)
    )
    assert completed.status == InventoryCountStatus.COMPLETED
    # Completing a count does not create LOSS movements.
    assert len(await inventory.list_all()) == 1
