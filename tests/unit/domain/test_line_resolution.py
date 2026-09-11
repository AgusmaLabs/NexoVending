"""Domain tests for pending / resolved replenishment line product identity."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from nexo_vending.domain.common.errors import (
    InvalidReplenishmentLineError,
    InvalidReplenishmentStateError,
)
from nexo_vending.domain.common.ids import (
    MachineId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    ReplenishmentLineId,
    SlotId,
    TenantId,
    UserId,
)
from nexo_vending.domain.common.value_objects import GeoLocation, SignedQuantity
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.replenishment.entities import Replenishment, ReplenishmentLine
from nexo_vending.domain.replenishment.enums import (
    LineResolutionStatus,
    ReplacementReason,
    ReplenishmentStatus,
)


def _machine_with_slot():
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=TenantId("tenant-a"),
        code="VM-P1",
        name="Pending",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 9, 11, tzinfo=UTC),
    )
    slot = machine.add_slot(
        slot_number=1,
        capacity=10,
        selling_price=SellingPrice(amount=Decimal("1500")),
    )
    return machine, slot


def _start(machine: Machine) -> Replenishment:
    return Replenishment.start(
        replenishment_id=ReplenishmentId.new(),
        operator_id=UserId.new(),
        machine=machine,
        started_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
        location=GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=4.0),
        idempotency_key="pending-key",
    )


def test_resolved_line_requires_product_id() -> None:
    with pytest.raises(InvalidReplenishmentLineError):
        ReplenishmentLine(
            id=ReplenishmentLineId.new(),
            machine_position_id=SlotId.new(),
            product_id=None,
            quantity=SignedQuantity(1),
            unit_price=Decimal("1"),
            occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            product_description_snapshot="x",
            resolution_status=LineResolutionStatus.RESOLVED,
        )


def test_pending_line_requires_manual_description() -> None:
    with pytest.raises(InvalidReplenishmentLineError):
        ReplenishmentLine(
            id=ReplenishmentLineId.new(),
            machine_position_id=SlotId.new(),
            product_id=None,
            quantity=SignedQuantity(1),
            unit_price=Decimal("1"),
            occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            product_description_snapshot="x",
            resolution_status=LineResolutionStatus.PENDING_PRODUCT_RESOLUTION,
            manual_description=None,
        )


def test_pending_line_rejects_empty_manual_description() -> None:
    with pytest.raises(InvalidReplenishmentLineError):
        ReplenishmentLine(
            id=ReplenishmentLineId.new(),
            machine_position_id=SlotId.new(),
            product_id=None,
            quantity=SignedQuantity(1),
            unit_price=Decimal("1"),
            occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            product_description_snapshot="x",
            resolution_status=LineResolutionStatus.PENDING_PRODUCT_RESOLUTION,
            manual_description="   ",
        )


def test_pending_line_rejects_replacement_reason() -> None:
    with pytest.raises(InvalidReplenishmentLineError):
        ReplenishmentLine(
            id=ReplenishmentLineId.new(),
            machine_position_id=SlotId.new(),
            product_id=None,
            quantity=SignedQuantity(1),
            unit_price=Decimal("1"),
            occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            product_description_snapshot="Energy",
            resolution_status=LineResolutionStatus.PENDING_PRODUCT_RESOLUTION,
            manual_description="Energy",
            replacement_reason=ReplacementReason.OUT_OF_STOCK,
        )


def test_cannot_construct_pending_with_product_id() -> None:
    with pytest.raises(InvalidReplenishmentLineError):
        ReplenishmentLine(
            id=ReplenishmentLineId.new(),
            machine_position_id=SlotId.new(),
            product_id=ProductId.new(),
            quantity=SignedQuantity(1),
            unit_price=Decimal("1"),
            occurred_at=datetime(2026, 9, 11, 12, 0, tzinfo=UTC),
            product_description_snapshot="Energy",
            resolution_status=LineResolutionStatus.PENDING_PRODUCT_RESOLUTION,
            manual_description="Energy",
        )


def test_add_pending_line_via_aggregate() -> None:
    machine, slot = _machine_with_slot()
    visit = _start(machine)
    line = visit.add_line(
        machine=machine,
        slot=slot,
        product_id=None,
        quantity=3,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 11, 12, 5, tzinfo=UTC),
        product_description_snapshot="ignored",
        manual_description="Bebida energética X",
    )
    assert line.is_pending_product_resolution
    assert line.product_id is None
    assert line.manual_description == "Bebida energética X"
    assert line.product_description_snapshot == "Bebida energética X"


def test_resolve_line_product_and_idempotent_same_product() -> None:
    machine, slot = _machine_with_slot()
    visit = _start(machine)
    line = visit.add_line(
        machine=machine,
        slot=slot,
        product_id=None,
        quantity=2,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 11, 12, 5, tzinfo=UTC),
        product_description_snapshot="x",
        manual_description="Unknown drink",
    )
    product_id = ProductId.new()
    resolved = visit.resolve_line_product(
        line_id=line.id,
        product_id=product_id,
        product_description_snapshot="Catalog Drink",
        resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
        resolved_by_operator_id=OperatorId.new(),
    )
    assert resolved.is_resolved
    assert resolved.product_id == product_id
    again = visit.resolve_line_product(
        line_id=line.id,
        product_id=product_id,
        product_description_snapshot="Catalog Drink",
        resolved_at=datetime(2026, 9, 11, 13, 5, tzinfo=UTC),
        resolved_by_operator_id=OperatorId.new(),
    )
    assert again.product_id == product_id


def test_resolve_conflict_different_product() -> None:
    machine, slot = _machine_with_slot()
    visit = _start(machine)
    line = visit.add_line(
        machine=machine,
        slot=slot,
        product_id=None,
        quantity=2,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 11, 12, 5, tzinfo=UTC),
        product_description_snapshot="x",
        manual_description="Unknown drink",
    )
    visit.resolve_line_product(
        line_id=line.id,
        product_id=ProductId.new(),
        product_description_snapshot="A",
        resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
        resolved_by_operator_id=OperatorId.new(),
    )
    with pytest.raises(InvalidReplenishmentLineError):
        visit.resolve_line_product(
            line_id=line.id,
            product_id=ProductId.new(),
            product_description_snapshot="B",
            resolved_at=datetime(2026, 9, 11, 13, 1, tzinfo=UTC),
            resolved_by_operator_id=OperatorId.new(),
        )


def test_resolve_rejected_for_cancelled_visit() -> None:
    machine, slot = _machine_with_slot()
    visit = _start(machine)
    line = visit.add_line(
        machine=machine,
        slot=slot,
        product_id=None,
        quantity=1,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 11, 12, 5, tzinfo=UTC),
        product_description_snapshot="x",
        manual_description="Unknown",
    )
    visit.cancel()
    with pytest.raises(InvalidReplenishmentStateError):
        visit.resolve_line_product(
            line_id=line.id,
            product_id=ProductId.new(),
            product_description_snapshot="A",
            resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
            resolved_by_operator_id=OperatorId.new(),
        )


def test_resolve_allowed_on_completed_visit() -> None:
    machine, slot = _machine_with_slot()
    visit = _start(machine)
    line = visit.add_line(
        machine=machine,
        slot=slot,
        product_id=None,
        quantity=1,
        unit_price=Decimal("1500"),
        occurred_at=datetime(2026, 9, 11, 12, 5, tzinfo=UTC),
        product_description_snapshot="x",
        manual_description="Unknown",
    )
    visit.complete(completed_at=datetime(2026, 9, 11, 12, 30, tzinfo=UTC))
    assert visit.status == ReplenishmentStatus.COMPLETED
    resolved = visit.resolve_line_product(
        line_id=line.id,
        product_id=ProductId.new(),
        product_description_snapshot="A",
        resolved_at=datetime(2026, 9, 11, 13, 0, tzinfo=UTC),
        resolved_by_operator_id=OperatorId.new(),
    )
    assert resolved.is_resolved
