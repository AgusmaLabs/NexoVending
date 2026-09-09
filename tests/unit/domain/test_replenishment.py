from datetime import UTC, datetime
from decimal import Decimal

import pytest

from nexo_vending.domain.common.errors import (
    CapacityExceededError,
    InactiveMachineError,
    InvalidQuantityError,
    InvalidReplenishmentStateError,
    SubstitutionRejectedError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId, ReplenishmentId, TenantId, UserId
from nexo_vending.domain.common.value_objects import GeoLocation, SignedQuantity
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.enums import ReplacementReason, ReplenishmentStatus


def _machine_with_slot(
    *,
    capacity: int = 5,
    preferred: ProductId | None = None,
    price: Decimal | None = Decimal("1500"),
    machine_type: MachineType = MachineType.SNACK,
) -> tuple[Machine, object]:
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=TenantId("tenant-a"),
        code="VM-S1",
        name="Snack 1",
        machine_type=machine_type,
        created_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    selling = SellingPrice(amount=price) if price is not None else None
    slot = machine.add_slot(
        slot_number=1,
        capacity=capacity,
        preferred_product_id=preferred,
        selling_price=selling,
    )
    return machine, slot


def _start(machine: Machine) -> Replenishment:
    return Replenishment.start(
        replenishment_id=ReplenishmentId.new(),
        operator_id=UserId.new(),
        machine=machine,
        started_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
        location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=4.0),
        idempotency_key="key-1",
    )


def test_rep_01_create_replenishment() -> None:
    machine, _ = _machine_with_slot()
    replenishment = _start(machine)
    assert replenishment.status == ReplenishmentStatus.IN_PROGRESS
    assert replenishment.machine_id == machine.id


def test_rep_02_add_positive_line() -> None:
    machine, slot = _machine_with_slot()
    replenishment = _start(machine)
    line = replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=ProductId.new(),
        quantity=SignedQuantity(5),
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        product_description_snapshot="Cola",
    )
    assert line.quantity.value == 5
    assert line.quantity.is_load


def test_rep_03_add_negative_line() -> None:
    machine, slot = _machine_with_slot()
    replenishment = _start(machine)
    line = replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=ProductId.new(),
        quantity=-3,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        product_description_snapshot="Cola",
    )
    assert line.quantity.value == -3
    assert line.quantity.is_unload


def test_rep_04_reject_zero_quantity() -> None:
    with pytest.raises(InvalidQuantityError):
        SignedQuantity(0)


def test_rep_05_complete() -> None:
    machine, _ = _machine_with_slot()
    replenishment = _start(machine)
    completed_at = datetime(2026, 9, 7, 13, 0, tzinfo=UTC)
    replenishment.complete(completed_at=completed_at)
    assert replenishment.status == ReplenishmentStatus.COMPLETED
    assert replenishment.completed_at == completed_at


def test_rep_06_cancel() -> None:
    machine, _ = _machine_with_slot()
    replenishment = _start(machine)
    replenishment.cancel()
    assert replenishment.status == ReplenishmentStatus.CANCELLED


def test_rep_07_08_immutable_after_terminal() -> None:
    machine, slot = _machine_with_slot()
    completed = _start(machine)
    completed.complete(completed_at=datetime(2026, 9, 7, 13, 0, tzinfo=UTC))
    with pytest.raises(InvalidReplenishmentStateError):
        completed.add_line(
            machine=machine,
            slot=slot,
            product_id=ProductId.new(),
            quantity=1,
            unit_price=Decimal("1500"),
            occurred_at=datetime(2026, 9, 7, 13, 1, tzinfo=UTC),
            product_description_snapshot="Cola",
        )
    cancelled = _start(machine)
    cancelled.cancel()
    with pytest.raises(InvalidReplenishmentStateError):
        cancelled.add_line(
            machine=machine,
            slot=slot,
            product_id=ProductId.new(),
            quantity=1,
            unit_price=Decimal("1500"),
            occurred_at=datetime(2026, 9, 7, 13, 1, tzinfo=UTC),
            product_description_snapshot="Cola",
        )


def test_inactive_machine_rejected() -> None:
    machine, _ = _machine_with_slot()
    machine.deactivate()
    with pytest.raises(InactiveMachineError):
        _start(machine)


def test_cap_rules() -> None:
    machine, slot = _machine_with_slot(capacity=5)
    replenishment = _start(machine)
    product = ProductId.new()
    at = datetime(2026, 9, 7, 12, 5, tzinfo=UTC)
    replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=product,
        quantity=5,
        unit_price="1500",
        occurred_at=at,
        product_description_snapshot="Cola",
    )
    with pytest.raises(CapacityExceededError):
        replenishment.add_line(
            machine=machine,
            slot=slot,
            product_id=product,
            quantity=6,
            unit_price="1500",
            occurred_at=at,
            product_description_snapshot="Cola",
        )
    replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=product,
        quantity=-5,
        unit_price="1500",
        occurred_at=at,
        product_description_snapshot="Cola",
    )
    with pytest.raises(CapacityExceededError):
        replenishment.add_line(
            machine=machine,
            slot=slot,
            product_id=product,
            quantity=-6,
            unit_price="1500",
            occurred_at=at,
            product_description_snapshot="Cola",
        )
    # CAP-06 multiple +5 valid independently
    replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=product,
        quantity=5,
        unit_price="1500",
        occurred_at=at,
        product_description_snapshot="Cola",
    )
    replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=product,
        quantity=5,
        unit_price="1500",
        occurred_at=at,
        product_description_snapshot="Cola",
    )


def test_sub_same_price_keeps_preferred() -> None:
    preferred = ProductId.new()
    actual = ProductId.new()
    machine, slot = _machine_with_slot(preferred=preferred, price=Decimal("1500"))
    replenishment = _start(machine)
    line = replenishment.add_line(
        machine=machine,
        slot=slot,
        product_id=actual,
        quantity=2,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        product_description_snapshot="Sprite",
        replacement_reason=ReplacementReason.OUT_OF_STOCK,
    )
    assert line.preferred_product_id_snapshot == preferred
    assert line.replacement_reason == ReplacementReason.OUT_OF_STOCK
    assert slot.preferred_product_id == preferred


def test_sub_price_mismatch_rejected() -> None:
    preferred = ProductId.new()
    machine, slot = _machine_with_slot(preferred=preferred, price=Decimal("1500"))
    replenishment = _start(machine)
    with pytest.raises(SubstitutionRejectedError):
        replenishment.add_line(
            machine=machine,
            slot=slot,
            product_id=ProductId.new(),
            quantity=2,
            unit_price=Decimal("1700"),
            occurred_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
            product_description_snapshot="Sprite",
            replacement_reason=ReplacementReason.OPERATIONAL_DECISION,
        )
