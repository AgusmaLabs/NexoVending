from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

from nexo_platform.identity.authentication import Principal

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
from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    MachineId,
    OperatorId,
    ProductId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation, Quantity
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.assignment import MachineAssignment
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus
from tests.support.fakes import (
    InMemoryInventoryRepository,
    InMemoryMachineAssignmentRepository,
    InMemoryMachineRepository,
    InMemoryProductLookup,
    InMemoryProductRepository,
    InMemoryReplenishmentRepository,
)


def _operator(tenant: str = "tenant-a") -> Operator:
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId(tenant),
        principal=Principal(provider="google", subject="op-1"),
        role=OperatorRole.OPERATOR,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()
    return operator


async def _assign(assignments, operator: Operator, machine: Machine) -> None:
    await assignments.save(
        MachineAssignment.create(
            tenant_id=operator.tenant_id,
            replenisher_id=operator.id,
            machine_id=machine.id,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )


def test_start_replenishment_idempotent() -> None:
    asyncio.run(_test_start_replenishment_idempotent())


async def _test_start_replenishment_idempotent() -> None:
    machines = InMemoryMachineRepository()
    replenishments = InMemoryReplenishmentRepository()
    assignments = InMemoryMachineAssignmentRepository()
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=TenantId("tenant-a"),
        code="VM-1",
        name="Lobby",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    await machines.save(machine)
    operator = _operator()
    await _assign(assignments, operator, machine)

    use_case = StartReplenishment(machines, replenishments, assignments)
    command = StartReplenishmentCommand(
        operator=operator,
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
    inventory = InMemoryInventoryRepository()
    assignments = InMemoryMachineAssignmentRepository()
    tenant_id = TenantId("tenant-a")
    operator = _operator()
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
    await _assign(assignments, operator, machine)
    await inventory.record_movement(
        InventoryMovement(
            id=InventoryMovementId.new(),
            tenant_id=tenant_id,
            product_id=product.id,
            quantity=Quantity(10),
            movement_type=InventoryMovementType.ASSIGNMENT,
            reference_type=InventoryReferenceType.ASSIGNMENT,
            reference_id="seed",
            occurred_at=datetime(2026, 9, 7, 11, 0, tzinfo=UTC),
            actor_id=operator.id,
            destination_location=InventoryLocation.replenisher(operator.id),
            idempotency_key="seed",
        )
    )

    started = await StartReplenishment(machines, replenishments, assignments).execute(
        StartReplenishmentCommand(
            operator=operator,
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
        inventory,
        products,
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

    completed = await CompleteReplenishment(replenishments, inventory).execute(
        CompleteReplenishmentCommand(
            replenishment_id=started.id,
            tenant_id=tenant_id,
            completed_at=datetime(2026, 9, 7, 12, 30, tzinfo=UTC),
        )
    )
    assert completed.status == ReplenishmentStatus.COMPLETED
    assert (
        await inventory.expected_quantity(InventoryLocation.replenisher(operator.id), product.id)
        == 7
    )

    other = await StartReplenishment(machines, replenishments, assignments).execute(
        StartReplenishmentCommand(
            operator=operator,
            machine_id=machine.id,
            started_at=datetime(2026, 9, 7, 14, 0, tzinfo=UTC),
            location=GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=2.0),
            idempotency_key="visit-3",
        )
    )
    cancelled = await CancelReplenishment(replenishments).execute(
        CancelReplenishmentCommand(
            replenishment_id=other.id,
            tenant_id=tenant_id,
        )
    )
    assert cancelled.status == ReplenishmentStatus.CANCELLED
