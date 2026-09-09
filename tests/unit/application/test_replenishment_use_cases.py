from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from nexo_vending.application.replenishment.add_line import (
    AddReplenishmentLine,
    AddReplenishmentLineCommand,
)
from nexo_vending.application.replenishment.cancel import (
    CancelReplenishment,
    CancelReplenishmentCommand,
)
from nexo_vending.application.replenishment.complete import (
    CompleteReplenishment,
    CompleteReplenishmentCommand,
)
from nexo_vending.application.replenishment.start import (
    StartReplenishment,
    StartReplenishmentCommand,
)
from nexo_vending.domain.common.ids import MachineId, ProductId, TenantId, UserId
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus
from tests.support.fakes import (
    InMemoryMachineRepository,
    InMemoryProductLookup,
    InMemoryProductRepository,
    InMemoryReplenishmentRepository,
)


def test_start_replenishment_idempotent() -> None:
    asyncio.run(_test_start_replenishment_idempotent())


async def _test_start_replenishment_idempotent() -> None:
    machines = InMemoryMachineRepository()
    replenishments = InMemoryReplenishmentRepository()
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=TenantId("tenant-a"),
        code="VM-1",
        name="Lobby",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    await machines.save(machine)

    use_case = StartReplenishment(machines, replenishments)
    command = StartReplenishmentCommand(
        operator_id=UserId.new(),
        machine_id=machine.id,
        started_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
        location=GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=2.0),
        idempotency_key="visit-1",
    )
    first = await use_case.execute(command)
    second = await use_case.execute(command)
    assert first.id == second.id
    assert first.status == ReplenishmentStatus.IN_PROGRESS


def test_add_line_complete_and_cancel_flow() -> None:
    asyncio.run(_test_add_line_complete_and_cancel_flow())


async def _test_add_line_complete_and_cancel_flow() -> None:
    products = InMemoryProductRepository()
    machines = InMemoryMachineRepository()
    replenishments = InMemoryReplenishmentRepository()
    tenant_id = TenantId("tenant-a")
    product = Product.create(
        product_id=ProductId.new(),
        tenant_id=tenant_id,
        barcode=Barcode("555"),
        name="Agua",
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    await products.save(product)
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=tenant_id,
        code="VM-2",
        name="Hall",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    slot = machine.add_slot(
        slot_number=1,
        capacity=12,
        selling_price=SellingPrice(amount=Decimal("1000")),
    )
    await machines.save(machine)

    started = await StartReplenishment(machines, replenishments).execute(
        StartReplenishmentCommand(
            operator_id=UserId.new(),
            machine_id=machine.id,
            started_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
            location=GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=2.0),
            idempotency_key="visit-2",
        )
    )

    updated = await AddReplenishmentLine(
        replenishments,
        machines,
        InMemoryProductLookup(products),
    ).execute(
        AddReplenishmentLineCommand(
            replenishment_id=started.id,
            tenant_id=tenant_id,
            barcode="555",
            quantity=3,
            slot_id=slot.id,
            unit_price=Decimal("1000"),
            scanned_at=datetime(2026, 9, 7, 12, 10, tzinfo=UTC),
        )
    )
    assert len(updated.lines) == 1
    assert updated.lines[0].product_id == product.id
    assert updated.lines[0].product_description_snapshot == "Agua"

    completed = await CompleteReplenishment(replenishments).execute(
        CompleteReplenishmentCommand(
            replenishment_id=started.id,
            completed_at=datetime(2026, 9, 7, 12, 30, tzinfo=UTC),
        )
    )
    assert completed.status == ReplenishmentStatus.COMPLETED
    assert completed.completed_at is not None

    # Separate visit for cancel path
    other = await StartReplenishment(machines, replenishments).execute(
        StartReplenishmentCommand(
            operator_id=UserId.new(),
            machine_id=machine.id,
            started_at=datetime(2026, 9, 7, 14, 0, tzinfo=UTC),
            location=GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=2.0),
            idempotency_key="visit-3",
        )
    )
    cancelled = await CancelReplenishment(replenishments).execute(
        CancelReplenishmentCommand(replenishment_id=other.id)
    )
    assert cancelled.status == ReplenishmentStatus.CANCELLED
