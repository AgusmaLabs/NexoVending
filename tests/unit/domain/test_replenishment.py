from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidQuantityError,
    InvalidReplenishmentLineError,
    InvalidReplenishmentStateError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId, ReplenishmentId, UserId
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation, Quantity
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus


def _snack_machine(*, active: bool = True) -> Machine:
    return Machine(
        id=MachineId.new(),
        code="VM-S1",
        name="Snack 1",
        type=MachineType.SNACK,
        active=active,
    )


def _coffee_machine() -> Machine:
    return Machine(
        id=MachineId.new(),
        code="VM-C1",
        name="Coffee 1",
        type=MachineType.COFFEE,
    )


def _location() -> GeoLocation:
    return GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=4.0)


def _start(machine: Machine) -> Replenishment:
    return Replenishment.start(
        replenishment_id=ReplenishmentId.new(),
        operator_id=UserId.new(),
        machine=machine,
        started_at=datetime(2026, 9, 7, 12, 0, tzinfo=UTC),
        location=_location(),
        idempotency_key="key-1",
    )


def test_create_replenishment() -> None:
    replenishment = _start(_snack_machine())
    assert replenishment.machine_id is not None
    assert replenishment.idempotency_key == "key-1"


def test_replenishment_starts_in_progress() -> None:
    assert _start(_snack_machine()).status == ReplenishmentStatus.IN_PROGRESS


def test_inactive_machine_rejected() -> None:
    with pytest.raises(InactiveMachineError):
        _start(_snack_machine(active=False))


def test_add_product_line() -> None:
    replenishment = _start(_snack_machine())
    line = replenishment.add_line(
        product_id=ProductId.new(),
        barcode_scanned=Barcode("123"),
        product_description_snapshot="Cola",
        manual_description=None,
        quantity=Quantity(2),
        slot=1,
        scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
    )
    assert len(replenishment.lines) == 1
    assert line.quantity.value == 2


def test_quantity_must_be_positive() -> None:
    replenishment = _start(_snack_machine())
    with pytest.raises(InvalidQuantityError):
        replenishment.add_line(
            product_id=ProductId.new(),
            barcode_scanned=None,
            product_description_snapshot="Cola",
            manual_description=None,
            quantity=Quantity(0),
            slot=1,
            scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        )


def test_snack_requires_slot() -> None:
    replenishment = _start(_snack_machine())
    with pytest.raises(InvalidReplenishmentLineError):
        replenishment.add_line(
            product_id=ProductId.new(),
            barcode_scanned=None,
            product_description_snapshot="Cola",
            manual_description=None,
            quantity=Quantity(1),
            slot=None,
            scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        )


def test_coffee_does_not_allow_slot() -> None:
    replenishment = _start(_coffee_machine())
    with pytest.raises(InvalidReplenishmentLineError):
        replenishment.add_line(
            product_id=ProductId.new(),
            barcode_scanned=None,
            product_description_snapshot="Coffee beans",
            manual_description=None,
            quantity=Quantity(1),
            slot=1,
            scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        )


def test_unknown_product_requires_description() -> None:
    replenishment = _start(_snack_machine())
    with pytest.raises(InvalidReplenishmentLineError):
        replenishment.add_line(
            product_id=None,
            barcode_scanned=Barcode("999"),
            product_description_snapshot="x",
            manual_description=None,
            quantity=Quantity(1),
            slot=1,
            scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
        )


def test_known_product_does_not_require_manual_description() -> None:
    replenishment = _start(_snack_machine())
    replenishment.add_line(
        product_id=ProductId.new(),
        barcode_scanned=Barcode("123"),
        product_description_snapshot="Cola",
        manual_description=None,
        quantity=Quantity(1),
        slot=2,
        scanned_at=datetime(2026, 9, 7, 12, 5, tzinfo=UTC),
    )
    assert replenishment.lines[0].manual_description is None


def test_completed_replenishment_cannot_add_lines() -> None:
    replenishment = _start(_snack_machine())
    replenishment.complete(completed_at=datetime(2026, 9, 7, 13, 0, tzinfo=UTC))
    with pytest.raises(InvalidReplenishmentStateError):
        replenishment.add_line(
            product_id=ProductId.new(),
            barcode_scanned=None,
            product_description_snapshot="Cola",
            manual_description=None,
            quantity=Quantity(1),
            slot=1,
            scanned_at=datetime(2026, 9, 7, 13, 1, tzinfo=UTC),
        )


def test_cancelled_replenishment_cannot_add_lines() -> None:
    replenishment = _start(_snack_machine())
    replenishment.cancel()
    with pytest.raises(InvalidReplenishmentStateError):
        replenishment.add_line(
            product_id=ProductId.new(),
            barcode_scanned=None,
            product_description_snapshot="Cola",
            manual_description=None,
            quantity=Quantity(1),
            slot=1,
            scanned_at=datetime(2026, 9, 7, 13, 1, tzinfo=UTC),
        )


def test_complete_replenishment() -> None:
    replenishment = _start(_snack_machine())
    completed_at = datetime(2026, 9, 7, 13, 0, tzinfo=UTC)
    replenishment.complete(completed_at=completed_at)
    assert replenishment.status == ReplenishmentStatus.COMPLETED


def test_completed_at_recorded() -> None:
    replenishment = _start(_snack_machine())
    completed_at = datetime(2026, 9, 7, 13, 0, tzinfo=UTC)
    replenishment.complete(completed_at=completed_at)
    assert replenishment.completed_at == completed_at
