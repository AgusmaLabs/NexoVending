from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from nexo_platform.identity.authentication import Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.application.machines.add_machine_slot import (
    AddMachineSlot,
    AddMachineSlotCommand,
)
from nexo_vending.application.machines.change_slot_capacity import (
    ChangeSlotCapacity,
    ChangeSlotCapacityCommand,
)
from nexo_vending.application.machines.create_machine import (
    CreateMachine,
    CreateMachineCommand,
)
from nexo_vending.application.machines.deactivate_machine import (
    DeactivateMachine,
    DeactivateMachineCommand,
)
from nexo_vending.application.machines.get_machine import (
    FindMachineByCode,
    FindMachineByCodeQuery,
    GetMachine,
    GetMachineQuery,
)
from nexo_vending.application.machines.set_preferred_product import (
    SetPreferredProduct,
    SetPreferredProductCommand,
)
from nexo_vending.application.machines.set_slot_selling_price import (
    SetSlotSellingPrice,
    SetSlotSellingPriceCommand,
)
from nexo_vending.domain.common.ids import OperatorId, ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.machines.enums import MachineStatus, MachineType
from nexo_vending.domain.machines.errors import CrossTenantMachineAccessError, MachineError
from nexo_vending.domain.products.entities import Product
from tests.support.fakes import InMemoryMachineRepository, InMemoryProductRepository


def _admin(tenant: str = "tenant-a") -> Operator:
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId(tenant),
        principal=Principal(provider="google", subject="ops-admin"),
        role=OperatorRole.ADMIN,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()
    return operator


def _context(tenant: str = "tenant-a") -> RequestContext:
    return RequestContext.from_principal(
        tenant_id=tenant,
        principal=Principal(provider="google", subject="ops-admin"),
    )


def test_create_and_get_machine() -> None:
    asyncio.run(_test_create_and_get_machine())


async def _test_create_and_get_machine() -> None:
    repo = InMemoryMachineRepository()
    created = await CreateMachine(repo).execute(
        CreateMachineCommand(
            context=_context(),
            acting_operator=_admin(),
            code="vm-100",
            name="Hall",
            machine_type=MachineType.MIXED,
            address="Floor 1",
            latitude=-33.4,
            longitude=-70.6,
            sii_id="SII-1",
        )
    )
    assert created.code.value == "VM-100"
    assert created.status == MachineStatus.ACTIVE
    found = await GetMachine(repo).execute(
        GetMachineQuery(context=_context(), machine_id=created.id)
    )
    assert found.id == created.id
    by_code = await FindMachineByCode(repo).execute(
        FindMachineByCodeQuery(context=_context(), code="VM-100")
    )
    assert by_code is not None


def test_machine_lifecycle_and_slots() -> None:
    asyncio.run(_test_machine_lifecycle_and_slots())


async def _test_machine_lifecycle_and_slots() -> None:
    repo = InMemoryMachineRepository()
    machine = await CreateMachine(repo).execute(
        CreateMachineCommand(
            context=_context(),
            acting_operator=_admin(),
            code="VM-200",
            name="Snack",
            machine_type=MachineType.SNACK,
        )
    )
    slot = await AddMachineSlot(repo).execute(
        AddMachineSlotCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
            slot_number=1,
            capacity=12,
            selling_price=Decimal("1500"),
        )
    )
    changed = await ChangeSlotCapacity(repo).execute(
        ChangeSlotCapacityCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
            slot_id=slot.id,
            capacity=8,
        )
    )
    assert changed.capacity == 8
    priced = await SetSlotSellingPrice(repo).execute(
        SetSlotSellingPriceCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
            slot_id=slot.id,
            amount=Decimal("1700"),
        )
    )
    assert priced.selling_price is not None
    assert priced.selling_price.amount == Decimal("1700")
    deactivated = await DeactivateMachine(repo).execute(
        DeactivateMachineCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
        )
    )
    assert deactivated.status == MachineStatus.INACTIVE


def test_set_preferred_product_tenant_and_active_rules() -> None:
    asyncio.run(_test_set_preferred_product_tenant_and_active_rules())


async def _test_set_preferred_product_tenant_and_active_rules() -> None:
    machines = InMemoryMachineRepository()
    products = InMemoryProductRepository()
    machine = await CreateMachine(machines).execute(
        CreateMachineCommand(
            context=_context(),
            acting_operator=_admin(),
            code="VM-300",
            name="Coffee",
            machine_type=MachineType.COFFEE,
        )
    )
    slot = await AddMachineSlot(machines).execute(
        AddMachineSlotCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
            slot_number=1,
            capacity=20,
        )
    )
    active = Product.create(
        product_id=ProductId.new(),
        tenant_id=TenantId("tenant-a"),
        barcode=Barcode("111"),
        name="Beans",
        created_at=datetime(2026, 9, 9, tzinfo=UTC),
    )
    await products.save(active)
    configured = await SetPreferredProduct(machines, products).execute(
        SetPreferredProductCommand(
            context=_context(),
            acting_operator=_admin(),
            machine_id=machine.id,
            slot_id=slot.id,
            product_id=active.id,
        )
    )
    assert configured.preferred_product_id == active.id

    other_tenant = Product.create(
        product_id=ProductId.new(),
        tenant_id=TenantId("tenant-b"),
        barcode=Barcode("222"),
        name="Other",
        created_at=datetime(2026, 9, 9, tzinfo=UTC),
    )
    await products.save(other_tenant)
    with pytest.raises(MachineError, match="same tenant"):
        await SetPreferredProduct(machines, products).execute(
            SetPreferredProductCommand(
                context=_context(),
                acting_operator=_admin(),
                machine_id=machine.id,
                slot_id=slot.id,
                product_id=other_tenant.id,
            )
        )

    active.deactivate()
    await products.save(active)
    with pytest.raises(MachineError, match="must be active"):
        await SetPreferredProduct(machines, products).execute(
            SetPreferredProductCommand(
                context=_context(),
                acting_operator=_admin(),
                machine_id=machine.id,
                slot_id=slot.id,
                product_id=active.id,
            )
        )


def test_tenant_isolation_on_get() -> None:
    asyncio.run(_test_tenant_isolation_on_get())


async def _test_tenant_isolation_on_get() -> None:
    repo = InMemoryMachineRepository()
    machine = await CreateMachine(repo).execute(
        CreateMachineCommand(
            context=_context("tenant-a"),
            acting_operator=_admin("tenant-a"),
            code="VM-A",
            name="A",
            machine_type=MachineType.SNACK,
        )
    )
    with pytest.raises(CrossTenantMachineAccessError):
        await GetMachine(repo).execute(
            GetMachineQuery(context=_context("tenant-b"), machine_id=machine.id)
        )


def test_create_rejects_claimed_tenant_override() -> None:
    asyncio.run(_test_create_rejects_claimed_tenant_override())


async def _test_create_rejects_claimed_tenant_override() -> None:
    with pytest.raises(OperatorAuthorizationError, match="cannot override tenant"):
        await CreateMachine(InMemoryMachineRepository()).execute(
            CreateMachineCommand(
                context=_context("tenant-a"),
                acting_operator=_admin("tenant-a"),
                code="VM-X",
                name="X",
                machine_type=MachineType.SNACK,
                claimed_tenant_id="tenant-b",
            )
        )


def test_request_context_propagates_tenant() -> None:
    asyncio.run(_test_request_context_propagates_tenant())


async def _test_request_context_propagates_tenant() -> None:
    context = _context("tenant-platform")
    assert RequestContext.__module__.startswith("nexo_platform.")
    machine = await CreateMachine(InMemoryMachineRepository()).execute(
        CreateMachineCommand(
            context=context,
            acting_operator=_admin("tenant-platform"),
            code="VM-P",
            name="Platform Bound",
            machine_type=MachineType.MIXED,
        )
    )
    assert machine.tenant_id.value == str(context.tenant_id)
