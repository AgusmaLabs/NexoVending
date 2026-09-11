"""PostgreSQL persistence tests for V8 transactional replenishment."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from nexo_platform.transaction import NestedTransactionError, TransactionConflict
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from nexo_vending.application.inventory.assign import AssignInventory, AssignInventoryCommand
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
    ProductId,
    TenantId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation, Quantity
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus
from nexo_vending.infrastructure.persistence import VendingPersistence, transactional_uow
from nexo_vending.infrastructure.persistence.models import (
    InventoryMovementORM,
    ReplenishmentORM,
)

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def migrated_engine(postgres_url: str):
    engine = create_engine(postgres_url, pool_pre_ping=True)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(cfg, "head")
    try:
        yield engine
    finally:
        command.downgrade(cfg, "base")
        engine.dispose()


@pytest.fixture()
def session_factory(migrated_engine):
    return sessionmaker(bind=migrated_engine, autoflush=False, autocommit=False)


def test_uow_shares_session_and_nested_raises(session_factory) -> None:
    asyncio.run(_test_uow_shares_session_and_nested_raises(session_factory))


async def _test_uow_shares_session_and_nested_raises(session_factory) -> None:
    session = session_factory()
    try:
        async with transactional_uow(session) as uow:
            assert uow.session is session
            with pytest.raises(NestedTransactionError):
                async with transactional_uow(session):
                    pass
    finally:
        session.close()


def test_complete_replenishment_commits_atomically(session_factory) -> None:
    asyncio.run(_test_complete_replenishment_commits_atomically(session_factory))


async def _seed(
    session: Session,
    *,
    tenant: str = "tenant-a",
) -> tuple[Product, Machine, UserId]:
    persistence = VendingPersistence.for_session(session)
    tenant_id = TenantId(tenant)
    product = Product.create(
        product_id=ProductId.new(),
        tenant_id=tenant_id,
        barcode=Barcode("7800001"),
        name="Coca",
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    await persistence.products.save(product)
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=tenant_id,
        code="MIX-001",
        name="Lobby",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 10, tzinfo=UTC),
    )
    machine.add_slot(
        slot_number=7,
        capacity=10,
        selling_price=SellingPrice(amount=Decimal("1500")),
    )
    await persistence.machines.save(machine)
    operator = UserId.new()
    await persistence.inventory.record_movement(
        InventoryMovement(
            id=InventoryMovementId.new(),
            tenant_id=tenant_id,
            product_id=product.id,
            quantity=Quantity(20),
            movement_type=InventoryMovementType.ASSIGNMENT,
            reference_type=InventoryReferenceType.ASSIGNMENT,
            reference_id="seed",
            occurred_at=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
            actor_id=operator,
            destination_location=InventoryLocation.replenisher(operator),
            idempotency_key=f"{tenant}:seed:{operator.value}",
        )
    )
    return product, machine, operator


async def _test_complete_replenishment_commits_atomically(session_factory) -> None:
    session = session_factory()
    product_id = None
    operator_id = None
    slot_id = None
    machine_id = None
    try:
        async with transactional_uow(session) as uow:
            persistence = VendingPersistence.for_session(uow.session)
            product, machine, operator = await _seed(session)
            product_id = product.id
            operator_id = operator
            slot = machine.slots[0]
            slot_id = slot.id
            machine_id = machine.id

            started = await StartReplenishment(
                persistence.machines,
                persistence.replenishments,
            ).execute(
                StartReplenishmentCommand(
                    operator_id=operator,
                    machine_id=machine.id,
                    started_at=datetime(2026, 9, 10, 9, 0, tzinfo=UTC),
                    location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0),
                    idempotency_key="R001",
                )
            )
            from nexo_vending.application.replenishment.add_line import (
                AddReplenishmentLine,
                AddReplenishmentLineCommand,
            )

            class _Lookup:
                async def find_by_barcode(self, tenant_id, barcode):
                    return await persistence.products.find_by_barcode(tenant_id, barcode)

            await AddReplenishmentLine(
                persistence.replenishments,
                persistence.machines,
                _Lookup(),
            ).execute(
                AddReplenishmentLineCommand(
                    replenishment_id=started.id,
                    tenant_id=TenantId("tenant-a"),
                    barcode="7800001",
                    quantity=10,
                    slot_id=slot.id,
                    unit_price=Decimal("1500"),
                    scanned_at=datetime(2026, 9, 10, 9, 5, tzinfo=UTC),
                )
            )
            completed = await CompleteReplenishment(
                persistence.replenishments,
                persistence.inventory,
            ).execute(
                CompleteReplenishmentCommand(
                    replenishment_id=started.id,
                    tenant_id=TenantId("tenant-a"),
                    completed_at=datetime(2026, 9, 10, 9, 10, tzinfo=UTC),
                )
            )
            assert completed.status == ReplenishmentStatus.COMPLETED
    finally:
        session.close()

    verify = session_factory()
    try:
        assert verify.execute(select(ReplenishmentORM)).scalars().one().status == "COMPLETED"
        movements = list(verify.execute(select(InventoryMovementORM)).scalars())
        assert len(movements) == 2  # seed + replenishment
        assert (
            await VendingPersistence.for_session(verify).inventory.expected_quantity(
                InventoryLocation.replenisher(operator_id),
                product_id,
            )
            == 10
        )
        assert (
            await VendingPersistence.for_session(verify).inventory.expected_quantity(
                InventoryLocation.machine_slot(machine_id, slot_id),
                product_id,
            )
            == 10
        )
    finally:
        verify.close()


def test_complete_replenishment_rollback(session_factory) -> None:
    asyncio.run(_test_complete_replenishment_rollback(session_factory))


async def _test_complete_replenishment_rollback(session_factory) -> None:
    session = session_factory()
    product = machine = operator = started = None
    try:
        async with transactional_uow(session):
            persistence = VendingPersistence.for_session(session)
            product, machine, operator = await _seed(session)
            started = await StartReplenishment(
                persistence.machines,
                persistence.replenishments,
            ).execute(
                StartReplenishmentCommand(
                    operator_id=operator,
                    machine_id=machine.id,
                    started_at=datetime(2026, 9, 10, 10, 0, tzinfo=UTC),
                    location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0),
                    idempotency_key="R-ROLLBACK",
                )
            )
        # committed seed+start
    finally:
        session.close()

    session2 = session_factory()
    try:
        with pytest.raises(RuntimeError, match="forced failure"):
            async with transactional_uow(session2):
                persistence = VendingPersistence.for_session(session2)
                loaded = await persistence.replenishments.get(started.id)
                assert loaded is not None
                loaded.complete(completed_at=datetime(2026, 9, 10, 10, 30, tzinfo=UTC))
                await persistence.replenishments.save(loaded)
                raise RuntimeError("forced failure")
    finally:
        session2.close()

    verify = session_factory()
    try:
        row = verify.get(ReplenishmentORM, started.id.value)
        assert row is not None
        assert row.status == "IN_PROGRESS"
        count = verify.execute(select(InventoryMovementORM)).scalars().all()
        assert len(count) == 1  # only seed
    finally:
        verify.close()


def test_idempotent_complete_and_tenant_isolation(session_factory) -> None:
    asyncio.run(_test_idempotent_complete_and_tenant_isolation(session_factory))


async def _test_idempotent_complete_and_tenant_isolation(session_factory) -> None:
    session = session_factory()
    try:
        async with transactional_uow(session):
            persistence = VendingPersistence.for_session(session)
            product, machine, operator = await _seed(session, tenant="tenant-a")
            slot = machine.slots[0]
            # Tenant B product/machine with same idempotency key namespace
            product_b, machine_b, operator_b = await _seed(session, tenant="tenant-b")

            from nexo_vending.application.replenishment.add_line import (
                AddReplenishmentLine,
                AddReplenishmentLineCommand,
            )

            class _Lookup:
                async def find_by_barcode(self, tenant_id, barcode):
                    return await persistence.products.find_by_barcode(tenant_id, barcode)

            started = await StartReplenishment(
                persistence.machines, persistence.replenishments
            ).execute(
                StartReplenishmentCommand(
                    operator_id=operator,
                    machine_id=machine.id,
                    started_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
                    location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0),
                    idempotency_key="SAME-KEY",
                )
            )
            await AddReplenishmentLine(
                persistence.replenishments, persistence.machines, _Lookup()
            ).execute(
                AddReplenishmentLineCommand(
                    replenishment_id=started.id,
                    tenant_id=TenantId("tenant-a"),
                    barcode="7800001",
                    quantity=5,
                    slot_id=slot.id,
                    unit_price=Decimal("1500"),
                    scanned_at=datetime(2026, 9, 10, 11, 1, tzinfo=UTC),
                )
            )
            use_case = CompleteReplenishment(persistence.replenishments, persistence.inventory)
            first = await use_case.execute(
                CompleteReplenishmentCommand(
                    replenishment_id=started.id,
                    tenant_id=TenantId("tenant-a"),
                    completed_at=datetime(2026, 9, 10, 11, 2, tzinfo=UTC),
                )
            )
            second = await use_case.execute(
                CompleteReplenishmentCommand(
                    replenishment_id=started.id,
                    tenant_id=TenantId("tenant-a"),
                    completed_at=datetime(2026, 9, 10, 11, 3, tzinfo=UTC),
                )
            )
            assert first.id == second.id
            # Tenant B can reuse same idempotency key
            started_b = await StartReplenishment(
                persistence.machines, persistence.replenishments
            ).execute(
                StartReplenishmentCommand(
                    operator_id=operator_b,
                    machine_id=machine_b.id,
                    started_at=datetime(2026, 9, 10, 11, 0, tzinfo=UTC),
                    location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0),
                    idempotency_key="SAME-KEY",
                )
            )
            assert started_b.id != started.id
            # Cross-tenant: A cannot see B machine by tenant-scoped list
            listed_a = await persistence.machines.list_by_tenant(TenantId("tenant-a"))
            assert {m.id for m in listed_a} == {machine.id}
            assert product_b.tenant_id.value == "tenant-b"
    finally:
        session.close()

    verify = session_factory()
    try:
        movements = list(verify.execute(select(InventoryMovementORM)).scalars())
        # seed A + seed B + one replenishment movement for A
        assert len(movements) == 3
        repl_moves = [m for m in movements if m.movement_type == "REPLENISHMENT"]
        assert len(repl_moves) == 1
    finally:
        verify.close()


def test_optimistic_locking_on_replenishment(session_factory) -> None:
    asyncio.run(_test_optimistic_locking_on_replenishment(session_factory))


async def _test_optimistic_locking_on_replenishment(session_factory) -> None:
    session = session_factory()
    try:
        async with transactional_uow(session):
            persistence = VendingPersistence.for_session(session)
            _product, machine, operator = await _seed(session)
            started = await StartReplenishment(
                persistence.machines, persistence.replenishments
            ).execute(
                StartReplenishmentCommand(
                    operator_id=operator,
                    machine_id=machine.id,
                    started_at=datetime(2026, 9, 10, 12, 0, tzinfo=UTC),
                    location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0),
                    idempotency_key="LOCK-1",
                )
            )
            assert started.version == 1
    finally:
        session.close()

    s1 = session_factory()
    s2 = session_factory()
    try:
        p1 = VendingPersistence.for_session(s1)
        p2 = VendingPersistence.for_session(s2)
        a = await p1.replenishments.get(started.id)
        b = await p2.replenishments.get(started.id)
        assert a is not None and b is not None
        a.cancel(cancelled_at=datetime(2026, 9, 10, 12, 5, tzinfo=UTC))
        await p1.replenishments.save(a)
        s1.commit()
        b.cancel(cancelled_at=datetime(2026, 9, 10, 12, 6, tzinfo=UTC))
        with pytest.raises(TransactionConflict):
            await p2.replenishments.save(b)
            s2.commit()
    finally:
        s1.close()
        s2.close()


def test_assign_inventory_persists(session_factory) -> None:
    asyncio.run(_test_assign_inventory_persists(session_factory))


async def _test_assign_inventory_persists(session_factory) -> None:
    session = session_factory()
    try:
        async with transactional_uow(session) as uow:
            persistence = VendingPersistence.for_session(uow.session)
            tenant_id = TenantId("tenant-a")
            product = Product.create(
                product_id=ProductId.new(),
                tenant_id=tenant_id,
                barcode=Barcode("999"),
                name="Agua",
                created_at=datetime(2026, 9, 10, tzinfo=UTC),
            )
            await persistence.products.save(product)
            admin = UserId.new()
            replenisher = UserId.new()
            await AssignInventory(persistence.inventory).execute(
                AssignInventoryCommand(
                    tenant_id=tenant_id,
                    product_id=product.id,
                    quantity=50,
                    replenisher_id=replenisher,
                    actor_id=admin,
                    occurred_at=datetime(2026, 9, 10, 13, 0, tzinfo=UTC),
                    reference_id="assign-1",
                    administrator_id=None,
                    idempotency_key="assign-1",
                )
            )
            balance = await persistence.inventory.expected_quantity(
                InventoryLocation.replenisher(replenisher),
                product.id,
            )
            assert balance == 50
    finally:
        session.close()
