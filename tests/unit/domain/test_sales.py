from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import InsufficientStockError, InvalidRecipeError
from nexo_vending.domain.common.ids import (
    CoffeeSaleId,
    MachineId,
    ProductId,
    SelectionId,
    SlotId,
    SnackSaleId,
)
from nexo_vending.domain.sales.entities import (
    Recipe,
    RecipeIngredient,
    register_coffee_sale,
    register_snack_sale,
    total_snack_consumption,
)


def test_snack_sale_without_sku() -> None:
    slot = SlotId.new()
    sale = register_snack_sale(
        sale_id=SnackSaleId.new(),
        machine_id=MachineId.new(),
        slot_id=slot,
        quantity=6,
        occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
        product_id=None,
    )
    assert sale.product_id is None
    assert sale.quantity.value == 6
    assert total_snack_consumption([sale], slot_id=slot) == 6


def test_coffee_single_and_multi_ingredient_scaled() -> None:
    coffee = ProductId.new()
    milk = ProductId.new()
    chocolate = ProductId.new()
    single = Recipe(
        selection_id=SelectionId.new(),
        name="Cafe",
        ingredients=(RecipeIngredient(product_id=coffee, quantity_per_unit=1),),
    )
    sale1 = register_coffee_sale(
        sale_id=CoffeeSaleId.new(),
        machine_id=MachineId.new(),
        recipe=single,
        quantity=2,
        occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
    )
    assert sale1.consumptions[0].quantity == 2

    recipe = Recipe(
        selection_id=SelectionId.new(),
        name="Mocaccino",
        ingredients=(
            RecipeIngredient(product_id=coffee, quantity_per_unit=1),
            RecipeIngredient(product_id=milk, quantity_per_unit=1),
            RecipeIngredient(product_id=chocolate, quantity_per_unit=1),
        ),
    )
    sale = register_coffee_sale(
        sale_id=CoffeeSaleId.new(),
        machine_id=MachineId.new(),
        recipe=recipe,
        quantity=5,
        occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
        available_stock={coffee: 10, milk: 10, chocolate: 10},
    )
    assert len(sale.consumptions) == 3
    assert {c.product_id: c.quantity for c in sale.consumptions} == {
        coffee: 5,
        milk: 5,
        chocolate: 5,
    }


def test_coffee_rejects_missing_recipe_and_insufficient_stock() -> None:
    with pytest.raises(InvalidRecipeError):
        register_coffee_sale(
            sale_id=CoffeeSaleId.new(),
            machine_id=MachineId.new(),
            recipe=None,
            quantity=1,
            occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
        )
    coffee = ProductId.new()
    recipe = Recipe(
        selection_id=SelectionId.new(),
        name="Cafe",
        ingredients=(RecipeIngredient(product_id=coffee, quantity_per_unit=2),),
    )
    with pytest.raises(InsufficientStockError):
        register_coffee_sale(
            sale_id=CoffeeSaleId.new(),
            machine_id=MachineId.new(),
            recipe=recipe,
            quantity=3,
            occurred_at=datetime(2026, 9, 7, tzinfo=UTC),
            available_stock={coffee: 4},
        )
