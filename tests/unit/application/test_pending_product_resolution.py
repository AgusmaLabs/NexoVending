"""Application tests for pending product resolution on replenishment."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from nexo_platform.identity.authentication import Principal

from nexo_vending.application.replenishment.add_line import (
    AddReplenishmentLine,
    AddReplenishmentLineCommand,
)
from nexo_vending.application.replenishment.complete import (
    CompleteReplenishment,
    CompleteReplenishmentCommand,
    deferred_resolve_idempotency_key,
)
from nexo_vending.application.replenishment.list_pending_lines import (
    ListPendingProductResolutions,
    ListPendingProductResolutionsQuery,
)
from nexo_vending.application.replenishment.resolve_line_product import (
    ResolveReplenishmentLineProduct,
    ResolveReplenishmentLineProductCommand,
)
from nexo_vending.application.replenishment.start import (
    StartReplenishment,
    StartReplenishmentCommand,
)
from nexo_vending.domain.common.errors import DomainError, InsufficientStockError
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
from nexo_vending.domain.replenishment.enums import LineResolutionStatus, ReplenishmentStatus
from tests.support.fakes import (
    InMemoryInventoryRepository,
    InMemoryMachineAssignmentRepository,
    InMemoryMachineRepository,
    InMemoryProductLookup,
    InMemoryProductRepository,
    InMemoryReplenishmentRepository,
)


def _operator(*, role: OperatorRole = OperatorRole.OPERATOR, subject: str = "op-1") -> Operator:
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId("tenant-a"),
        principal=Principal(provider="google", subject=subject),
        role=role,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()
    return operator


async def _seed_world(*, stock: int = 50):
    products = InMemoryProductRepository()
    machines = InMemoryMachineRepository()
    replenishments = InMemoryReplenishmentRepository()
    inventory = InMemoryInventoryRepository()
    assignments = InMemoryMachineAssignmentRepository()
    tenant_id = TenantId("tenant-a")
    operator = _operator()
    admin = _operator(role=OperatorRole.ADMIN, subject="admin-1")
    product = Product.create(
        product_id=ProductId.new(),
        tenant_id=tenant_id,
        barcode=Barcode("555"),
        name="Agua",
        created_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    await products.save(product)
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=tenant_id,
        code="VM-2",
        name="Hall",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    slot = machine.add_slot(
        slot_number=1,
        capacity=12,
        selling_price=SellingPrice(amount=Decimal("1000")),
    )
    await machines.save(machine)
    await assignments.save(
        MachineAssignment.create(
            tenant_id=tenant_id,
            replenisher_id=operator.id,
            machine_id=machine.id,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
    )
    if stock:
        await inventory.record_movement(
            InventoryMovement(
                id=InventoryMovementId.new(),
                tenant_id=tenant_id,
                product_id=product.id,
                quantity=Quantity(stock),
                movement_type=InventoryMovementType.ASSIGNMENT,
                reference_type=InventoryReferenceType.ASSIGNMENT,
                reference_id="seed",
                occurred_at=datetime(2026, 9, 11, 8, 0, tzinfo=UTC),
                actor_id=admin.id,
                destination_location=InventoryLocation.replenisher(operator.id),
                idempotency_key="seed",
            )
        )
    visit = await StartReplenishment(machines, replenishments, assignments).execute(
        StartReplenishmentCommand(
            operator=operator,
            machine_id=machine.id,
            started_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            location=GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=2.0),
            idempotency_key="visit-pending",
        )
    )
    return {
        "products": products,
        "machines": machines,
        "replenishments": replenishments,
        "inventory": inventory,
        "tenant_id": tenant_id,
        "operator": operator,
        "admin": admin,
        "product": product,
        "machine": machine,
        "slot": slot,
        "visit": visit,
        "lookup": InMemoryProductLookup(products),
    }


def test_add_pending_line_when_barcode_unknown_with_manual_description() -> None:
    asyncio.run(_test_add_pending_barcode_unknown())


async def _test_add_pending_barcode_unknown() -> None:
    world = await _seed_world()
    use_case = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    result = await use_case.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=3,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            barcode="999999",
            manual_description="Bebida energética X",
        )
    )
    line = result.lines[0]
    assert line.resolution_status == LineResolutionStatus.PENDING_PRODUCT_RESOLUTION
    assert line.product_id is None


def test_add_pending_line_without_barcode_with_manual_description() -> None:
    asyncio.run(_test_add_pending_manual_only())


async def _test_add_pending_manual_only() -> None:
    world = await _seed_world()
    use_case = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    result = await use_case.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=2,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            manual_description="Unreadable wrapper",
        )
    )
    assert result.lines[0].is_pending_product_resolution


def test_reject_unknown_barcode_without_manual_description() -> None:
    asyncio.run(_test_reject_unknown_barcode())


async def _test_reject_unknown_barcode() -> None:
    world = await _seed_world()
    use_case = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    with pytest.raises(DomainError, match="product not found"):
        await use_case.execute(
            AddReplenishmentLineCommand(
                replenishment_id=world["visit"].id,
                tenant_id=world["tenant_id"],
                slot_id=world["slot"].id,
                quantity=1,
                scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
                barcode="999999",
            )
        )


def test_pending_line_skips_replenisher_stock_check() -> None:
    asyncio.run(_test_pending_skips_stock())


async def _test_pending_skips_stock() -> None:
    world = await _seed_world(stock=0)
    use_case = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    result = await use_case.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=5,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            manual_description="No stock check",
        )
    )
    assert result.lines[0].is_pending_product_resolution


def test_complete_writes_movements_only_for_resolved_lines() -> None:
    asyncio.run(_test_complete_mixed_lines())


async def _test_complete_mixed_lines() -> None:
    world = await _seed_world()
    add = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=2,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            product_id=world["product"].id,
        )
    )
    await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=1,
            scanned_at=datetime(2026, 9, 11, 12, 11, tzinfo=UTC),
            manual_description="Pending drink",
        )
    )
    completed = await CompleteReplenishment(
        world["replenishments"], world["inventory"]
    ).execute(
        CompleteReplenishmentCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            completed_at=datetime(2026, 9, 11, 12, 30, tzinfo=UTC),
        )
    )
    assert completed.status == ReplenishmentStatus.COMPLETED
    pending = [line for line in completed.lines if line.is_pending_product_resolution]
    assert len(pending) == 1
    movements = [
        m
        for m in world["inventory"]._movements
        if m.movement_type == InventoryMovementType.REPLENISHMENT
    ]
    assert len(movements) == 1
    assert movements[0].product_id == world["product"].id


def test_complete_then_resolve_produces_single_deferred_movement() -> None:
    asyncio.run(_test_complete_then_resolve())


async def _test_complete_then_resolve() -> None:
    world = await _seed_world()
    add = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    visit = await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=4,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            manual_description="Pending drink",
        )
    )
    await CompleteReplenishment(world["replenishments"], world["inventory"]).execute(
        CompleteReplenishmentCommand(
            replenishment_id=visit.id,
            tenant_id=world["tenant_id"],
            completed_at=datetime(2026, 9, 11, 12, 30, tzinfo=UTC),
        )
    )
    line_id = visit.lines[0].id
    resolved = await ResolveReplenishmentLineProduct(
        world["replenishments"], world["products"], world["inventory"]
    ).execute(
        ResolveReplenishmentLineProductCommand(
            tenant_id=world["tenant_id"],
            replenishment_id=visit.id,
            line_id=line_id,
            product_id=world["product"].id,
            resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
            actor_operator_id=world["admin"].id,
        )
    )
    assert resolved.lines[0].is_resolved
    movements = [
        m
        for m in world["inventory"]._movements
        if m.movement_type == InventoryMovementType.REPLENISHMENT
    ]
    assert len(movements) == 1
    assert movements[0].idempotency_key.endswith(":resolve")
    assert deferred_resolve_idempotency_key(resolved, resolved.lines[0]) == movements[
        0
    ].idempotency_key


def test_resolve_insufficient_stock_rolls_back_line_state() -> None:
    asyncio.run(_test_resolve_insufficient_stock())


async def _test_resolve_insufficient_stock() -> None:
    world = await _seed_world(stock=1)
    add = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    visit = await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=5,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            manual_description="Needs stock",
        )
    )
    await CompleteReplenishment(world["replenishments"], world["inventory"]).execute(
        CompleteReplenishmentCommand(
            replenishment_id=visit.id,
            tenant_id=world["tenant_id"],
            completed_at=datetime(2026, 9, 11, 12, 30, tzinfo=UTC),
        )
    )
    with pytest.raises(InsufficientStockError):
        await ResolveReplenishmentLineProduct(
            world["replenishments"], world["products"], world["inventory"]
        ).execute(
            ResolveReplenishmentLineProductCommand(
                tenant_id=world["tenant_id"],
                replenishment_id=visit.id,
                line_id=visit.lines[0].id,
                product_id=world["product"].id,
                resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
                actor_operator_id=world["admin"].id,
            )
        )
    reloaded = await world["replenishments"].get(visit.id)
    assert reloaded is not None
    assert reloaded.lines[0].is_pending_product_resolution
    assert not any(
        m.movement_type == InventoryMovementType.REPLENISHMENT
        for m in world["inventory"]._movements
    )


def test_list_pending_excludes_resolved() -> None:
    asyncio.run(_test_list_pending())


async def _test_list_pending() -> None:
    world = await _seed_world()
    add = AddReplenishmentLine(
        world["replenishments"],
        world["machines"],
        world["lookup"],
        world["inventory"],
        world["products"],
    )
    await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=1,
            scanned_at=datetime(2026, 9, 11, 12, 10, tzinfo=UTC),
            manual_description="Pending",
        )
    )
    await add.execute(
        AddReplenishmentLineCommand(
            replenishment_id=world["visit"].id,
            tenant_id=world["tenant_id"],
            slot_id=world["slot"].id,
            quantity=1,
            scanned_at=datetime(2026, 9, 11, 12, 11, tzinfo=UTC),
            product_id=world["product"].id,
        )
    )
    items = await ListPendingProductResolutions(world["replenishments"]).execute(
        ListPendingProductResolutionsQuery(tenant_id=world["tenant_id"])
    )
    assert len(items) == 1
    assert items[0].manual_description == "Pending"
