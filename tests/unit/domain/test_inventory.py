from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import InsufficientStockError, InvalidQuantityError
from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    MachineId,
    ProductId,
    SlotId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.custody import CustodyInventory
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.inventory.locations import InventoryLocation


def _now() -> datetime:
    return datetime(2026, 9, 7, 10, 0, tzinfo=UTC)


def _move(
    *,
    product_id: ProductId,
    quantity: int,
    movement_type: InventoryMovementType,
    actor: UserId,
    source: InventoryLocation | None = None,
    destination: InventoryLocation | None = None,
) -> InventoryMovement:
    return InventoryMovement(
        id=InventoryMovementId.new(),
        product_id=product_id,
        quantity=Quantity(quantity),
        movement_type=movement_type,
        reference_type=InventoryReferenceType.MANUAL,
        reference_id="ref-1",
        occurred_at=_now(),
        actor_id=actor,
        source_location=source,
        destination_location=destination,
    )


def test_inv_assignment_and_balances() -> None:
    admin = UserId.new()
    replenisher = UserId.new()
    product = ProductId.new()
    movements = [
        _move(
            product_id=product,
            quantity=100,
            movement_type=InventoryMovementType.ADJUSTMENT,
            actor=admin,
            destination=InventoryLocation.administrator(admin),
        ),
        _move(
            product_id=product,
            quantity=30,
            movement_type=InventoryMovementType.ASSIGNMENT,
            actor=admin,
            source=InventoryLocation.administrator(admin),
            destination=InventoryLocation.replenisher(replenisher),
        ),
    ]
    assert CustodyInventory.administrator_expected(
        movements, administrator_id=admin, product_id=product
    ) == 70
    assert CustodyInventory.replenisher_expected(
        movements, replenisher_id=replenisher, product_id=product
    ) == 30


def test_inv_replenishment_slot_removal_return_loss() -> None:
    admin = UserId.new()
    replenisher = UserId.new()
    product = ProductId.new()
    machine = MachineId.new()
    slot = SlotId.new()
    machine_loc = InventoryLocation.machine_slot(machine, slot)
    movements = [
        _move(
            product_id=product,
            quantity=30,
            movement_type=InventoryMovementType.ASSIGNMENT,
            actor=admin,
            source=InventoryLocation.administrator(admin),
            destination=InventoryLocation.replenisher(replenisher),
        ),
        _move(
            product_id=product,
            quantity=10,
            movement_type=InventoryMovementType.REPLENISHMENT,
            actor=replenisher,
            source=InventoryLocation.replenisher(replenisher),
            destination=machine_loc,
        ),
        _move(
            product_id=product,
            quantity=3,
            movement_type=InventoryMovementType.SLOT_REMOVAL,
            actor=replenisher,
            source=machine_loc,
            destination=InventoryLocation.replenisher(replenisher),
        ),
        _move(
            product_id=product,
            quantity=5,
            movement_type=InventoryMovementType.RETURN,
            actor=replenisher,
            source=InventoryLocation.replenisher(replenisher),
            destination=InventoryLocation.administrator(admin),
        ),
        _move(
            product_id=product,
            quantity=1,
            movement_type=InventoryMovementType.LOSS,
            actor=replenisher,
            source=InventoryLocation.replenisher(replenisher),
        ),
    ]
    # replenisher: +30 -10 +3 -5 -1 = 17
    assert CustodyInventory.replenisher_expected(
        movements, replenisher_id=replenisher, product_id=product
    ) == 17
    assert InventoryLedger.is_slot_removal(movements[2])
    assert not InventoryLedger.is_loss(movements[2])
    assert InventoryLedger.is_loss(movements[4])


def test_inv_negative_stock_rejected() -> None:
    replenisher = UserId.new()
    product = ProductId.new()
    existing = [
        _move(
            product_id=product,
            quantity=2,
            movement_type=InventoryMovementType.ASSIGNMENT,
            actor=replenisher,
            destination=InventoryLocation.replenisher(replenisher),
        )
    ]
    depleting = _move(
        product_id=product,
        quantity=3,
        movement_type=InventoryMovementType.REPLENISHMENT,
        actor=replenisher,
        source=InventoryLocation.replenisher(replenisher),
        destination=InventoryLocation.machine_slot(MachineId.new(), SlotId.new()),
    )
    with pytest.raises(InsufficientStockError):
        InventoryLedger.ensure_can_apply(existing, depleting)


def test_inv_immutable_and_positive_qty() -> None:
    movement = _move(
        product_id=ProductId.new(),
        quantity=1,
        movement_type=InventoryMovementType.ADJUSTMENT,
        actor=UserId.new(),
        destination=InventoryLocation.administrator(UserId.new()),
    )
    with pytest.raises(FrozenInstanceError):
        movement.quantity = Quantity(2)  # type: ignore[misc]
    with pytest.raises(InvalidQuantityError):
        Quantity(0)


def test_custody_transfer_conserves_total() -> None:
    admin = UserId.new()
    replenisher = UserId.new()
    product = ProductId.new()
    movements = [
        _move(
            product_id=product,
            quantity=40,
            movement_type=InventoryMovementType.ADJUSTMENT,
            actor=admin,
            destination=InventoryLocation.administrator(admin),
        ),
        _move(
            product_id=product,
            quantity=15,
            movement_type=InventoryMovementType.ASSIGNMENT,
            actor=admin,
            source=InventoryLocation.administrator(admin),
            destination=InventoryLocation.replenisher(replenisher),
        ),
    ]
    total = CustodyInventory.administrator_expected(
        movements, administrator_id=admin, product_id=product
    ) + CustodyInventory.replenisher_expected(
        movements, replenisher_id=replenisher, product_id=product
    )
    assert total == 40
