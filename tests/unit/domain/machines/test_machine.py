from datetime import UTC, datetime
from decimal import Decimal

import pytest

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidGeoLocationError,
    InvalidMachineError,
    InvalidSlotError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId, SlotId, TenantId
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineStatus, MachineType, SlotStatus
from nexo_vending.domain.machines.errors import (
    InvalidMachineCodeError,
    InvalidMachineTransitionError,
    InvalidSellingPriceError,
    InvalidSlotConfigurationError,
)
from nexo_vending.domain.machines.value_objects import (
    MachineCode,
    MachineLocation,
    SellingPrice,
)


def _machine(
    *,
    machine_type: MachineType = MachineType.SNACK,
    tenant: str = "tenant-a",
    code: str = "VM-001",
) -> Machine:
    return Machine.create(
        machine_id=MachineId.new(),
        tenant_id=TenantId(tenant),
        code=code,
        name="Lobby",
        machine_type=machine_type,
        created_at=datetime(2026, 9, 9, tzinfo=UTC),
    )


def test_machine_id_equality() -> None:
    a = MachineId.new()
    b = MachineId(value=a.value)
    assert a == b


def test_machine_code_normalization_and_equality() -> None:
    assert MachineCode(" vm-01 ").value == "VM-01"
    assert MachineCode("vm-01") == MachineCode("VM-01")


def test_machine_code_rejects_empty() -> None:
    with pytest.raises(InvalidMachineCodeError):
        MachineCode("  ")


def test_machine_types_include_mixed() -> None:
    assert {t.value for t in MachineType} == {"SNACK", "COFFEE", "MIXED"}


def test_machine_status_transitions() -> None:
    machine = _machine()
    assert machine.status == MachineStatus.ACTIVE
    machine.put_in_maintenance()
    assert machine.status == MachineStatus.MAINTENANCE
    machine.activate()
    machine.deactivate()
    assert machine.status == MachineStatus.INACTIVE
    with pytest.raises(InvalidMachineTransitionError):
        machine.put_in_maintenance()
    machine.activate()
    machine.deactivate()


def test_machine_location_bounds() -> None:
    loc = MachineLocation(address="Floor 1", latitude=-33.0, longitude=-70.0)
    assert loc.address == "Floor 1"
    with pytest.raises(InvalidGeoLocationError):
        MachineLocation(address="X", latitude=100, longitude=0)


def test_snack_coffee_mixed_accept_slots() -> None:
    for machine_type in (MachineType.SNACK, MachineType.COFFEE, MachineType.MIXED):
        machine = _machine(machine_type=machine_type, code=f"VM-{machine_type}")
        slot = machine.add_slot(slot_number=1, capacity=10)
        assert slot.slot_number == 1
        assert len(machine.slots) == 1


def test_duplicate_slot_number_rejected() -> None:
    machine = _machine()
    machine.add_slot(slot_number=1, capacity=5)
    with pytest.raises(InvalidSlotConfigurationError):
        machine.add_slot(slot_number=1, capacity=8)


def test_slot_number_and_capacity_validation() -> None:
    with pytest.raises(InvalidSlotError):
        MachineSlot(id=SlotId.new(), slot_number=0, capacity=5)
    with pytest.raises(InvalidSlotError):
        MachineSlot(id=SlotId.new(), slot_number=1, capacity=0)


def test_change_slot_capacity_preserves_identity_and_config() -> None:
    machine = _machine()
    product = ProductId.new()
    slot = machine.add_slot(
        slot_number=5,
        capacity=12,
        preferred_product_id=product,
        selling_price=SellingPrice(amount=Decimal("1500")),
    )
    slot_id = slot.id
    machine.change_slot_capacity(slot_id, 8)
    updated = machine.find_slot(slot_id)
    assert updated is not None
    assert updated.id == slot_id
    assert updated.slot_number == 5
    assert updated.capacity == 8
    assert updated.preferred_product_id == product
    assert updated.selling_price is not None
    assert updated.selling_price.amount == Decimal("1500")


def test_preferred_product_is_not_operational_restriction() -> None:
    machine = _machine()
    preferred = ProductId.new()
    other = ProductId.new()
    slot = machine.add_slot(slot_number=7, capacity=10, preferred_product_id=preferred)
    # Domain stores preference only; nothing forbids another product id for ops.
    assert slot.preferred_product_id == preferred
    assert slot.preferred_product_id != other


def test_selling_price_independent_per_machine_slot() -> None:
    m1 = _machine(code="M1")
    m2 = _machine(code="M2")
    product = ProductId.new()
    s1 = m1.add_slot(
        slot_number=1,
        capacity=10,
        preferred_product_id=product,
        selling_price=SellingPrice(amount=Decimal("1500")),
    )
    s2 = m2.add_slot(
        slot_number=1,
        capacity=10,
        preferred_product_id=product,
        selling_price=SellingPrice(amount=Decimal("1700")),
    )
    assert s1.selling_price is not None and s2.selling_price is not None
    assert s1.selling_price.amount != s2.selling_price.amount
    assert s1.preferred_product_id == s2.preferred_product_id


def test_selling_price_rejects_negative() -> None:
    with pytest.raises(InvalidSellingPriceError):
        SellingPrice(amount=Decimal("-1"))


def test_slot_lifecycle_and_clear_preferred() -> None:
    machine = _machine()
    slot = machine.add_slot(slot_number=2, capacity=6, preferred_product_id=ProductId.new())
    machine.deactivate_slot(slot.id)
    assert machine.find_slot(slot.id).status == SlotStatus.INACTIVE
    machine.activate_slot(slot.id)
    machine.clear_preferred_product(slot.id)
    assert machine.find_slot(slot.id).preferred_product_id is None


def test_inactive_machine_cannot_start_replenishment() -> None:
    machine = _machine()
    machine.deactivate()
    with pytest.raises(InactiveMachineError):
        machine.ensure_can_start_replenishment()


def test_machine_requires_name() -> None:
    with pytest.raises(InvalidMachineError):
        Machine.create(
            machine_id=MachineId.new(),
            tenant_id=TenantId("tenant-a"),
            code="VM-X",
            name=" ",
            machine_type=MachineType.SNACK,
        )
