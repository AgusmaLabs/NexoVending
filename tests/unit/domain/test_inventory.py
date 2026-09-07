from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import InsufficientStockError, InvalidQuantityError
from nexo_vending.domain.common.ids import InventoryMovementId, ProductId, UserId
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType
from nexo_vending.domain.inventory.ledger import InventoryLedger


def _movement(
    *,
    operator_id: UserId,
    product_id: ProductId,
    movement_type: InventoryMovementType,
    quantity: int,
) -> InventoryMovement:
    return InventoryMovement(
        id=InventoryMovementId.new(),
        operator_id=operator_id,
        product_id=product_id,
        movement_type=movement_type,
        quantity=Quantity(quantity),
        reference="test",
        created_at=datetime(2026, 9, 7, 10, 0, tzinfo=UTC),
        created_by=operator_id,
    )


def test_assignment_increases_stock() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=10,
        )
    ]
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 10


def test_replenishment_decreases_stock() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=10,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.REPLENISHMENT,
            quantity=3,
        ),
    ]
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 7


def test_return_increases_stock() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.RETURN,
            quantity=2,
        )
    ]
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 2


def test_loss_decreases_stock() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=5,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.LOSS,
            quantity=2,
        ),
    ]
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 3


def test_adjustment() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ADJUSTMENT,
            quantity=4,
        )
    ]
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 4


def test_stock_calculation() -> None:
    operator = UserId.new()
    product = ProductId.new()
    movements = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=10,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.RETURN,
            quantity=2,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ADJUSTMENT,
            quantity=1,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.REPLENISHMENT,
            quantity=5,
        ),
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.LOSS,
            quantity=1,
        ),
    ]
    # 10 + 2 + 1 - 5 - 1 = 7
    assert InventoryLedger.stock_for(movements, operator_id=operator, product_id=product) == 7


def test_negative_stock_rejected() -> None:
    operator = UserId.new()
    product = ProductId.new()
    existing = [
        _movement(
            operator_id=operator,
            product_id=product,
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=2,
        )
    ]
    depleting = _movement(
        operator_id=operator,
        product_id=product,
        movement_type=InventoryMovementType.REPLENISHMENT,
        quantity=3,
    )
    with pytest.raises(InsufficientStockError):
        InventoryLedger.ensure_can_apply(existing, depleting)


def test_inventory_movement_is_immutable() -> None:
    movement = _movement(
        operator_id=UserId.new(),
        product_id=ProductId.new(),
        movement_type=InventoryMovementType.ASSIGNMENT,
        quantity=1,
    )
    with pytest.raises(FrozenInstanceError):
        movement.quantity = Quantity(2)  # type: ignore[misc]


def test_movement_quantity_must_be_positive() -> None:
    with pytest.raises(InvalidQuantityError):
        _movement(
            operator_id=UserId.new(),
            product_id=ProductId.new(),
            movement_type=InventoryMovementType.ASSIGNMENT,
            quantity=0,
        )
