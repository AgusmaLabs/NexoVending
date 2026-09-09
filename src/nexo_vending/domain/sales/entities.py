from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from nexo_vending.domain.common.errors import (
    InsufficientStockError,
    InvalidRecipeError,
    InvalidSaleError,
)
from nexo_vending.domain.common.ids import (
    CoffeeSaleId,
    MachineId,
    ProductId,
    SelectionId,
    SlotId,
    SnackSaleId,
)
from nexo_vending.domain.common.value_objects import Quantity, require_aware


@dataclass(frozen=True, slots=True)
class RecipeIngredient:
    product_id: ProductId
    quantity_per_unit: int

    def __post_init__(self) -> None:
        if self.quantity_per_unit <= 0:
            raise InvalidRecipeError("ingredient quantity_per_unit must be > 0")


@dataclass(frozen=True, slots=True)
class Recipe:
    selection_id: SelectionId
    name: str
    ingredients: tuple[RecipeIngredient, ...]

    def __post_init__(self) -> None:
        cleaned = self.name.strip()
        if not cleaned:
            raise InvalidRecipeError("recipe name is required")
        if not self.ingredients:
            raise InvalidRecipeError("recipe requires at least one ingredient")
        object.__setattr__(self, "name", cleaned)

    def consumption_for(self, sold_units: int) -> dict[ProductId, int]:
        if sold_units <= 0:
            raise InvalidSaleError("sold quantity must be > 0")
        return {
            item.product_id: item.quantity_per_unit * sold_units
            for item in self.ingredients
        }


@dataclass(frozen=True, slots=True)
class SnackSale:
    """Snack sale by slot. product_id may be unknown; do not invent SKU attribution."""

    id: SnackSaleId
    machine_id: MachineId
    slot_id: SlotId
    quantity: Quantity
    occurred_at: datetime
    product_id: ProductId | None = None

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field_name="occurred_at")


@dataclass(frozen=True, slots=True)
class IngredientConsumption:
    product_id: ProductId
    quantity: int
    container_id: SlotId | None = None


@dataclass(frozen=True, slots=True)
class CoffeeSale:
    id: CoffeeSaleId
    machine_id: MachineId
    selection_id: SelectionId
    quantity: Quantity
    occurred_at: datetime
    consumptions: tuple[IngredientConsumption, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field_name="occurred_at")


def register_snack_sale(
    *,
    sale_id: SnackSaleId,
    machine_id: MachineId,
    slot_id: SlotId,
    quantity: int,
    occurred_at: datetime,
    product_id: ProductId | None = None,
) -> SnackSale:
    return SnackSale(
        id=sale_id,
        machine_id=machine_id,
        slot_id=slot_id,
        quantity=Quantity(quantity),
        occurred_at=occurred_at,
        product_id=product_id,
    )


def register_coffee_sale(
    *,
    sale_id: CoffeeSaleId,
    machine_id: MachineId,
    recipe: Recipe | None,
    quantity: int,
    occurred_at: datetime,
    available_stock: dict[ProductId, int] | None = None,
    container_by_product: dict[ProductId, SlotId] | None = None,
) -> CoffeeSale:
    if recipe is None:
        raise InvalidRecipeError("coffee sale requires a valid recipe")
    sold = Quantity(quantity)
    planned = recipe.consumption_for(sold.value)
    stock = available_stock or {}
    containers = container_by_product or {}
    consumptions: list[IngredientConsumption] = []
    for product_id, needed in planned.items():
        on_hand = stock.get(product_id)
        if on_hand is not None and on_hand < needed:
            raise InsufficientStockError(
                f"insufficient stock for ingredient {product_id.value}"
            )
        consumptions.append(
            IngredientConsumption(
                product_id=product_id,
                quantity=needed,
                container_id=containers.get(product_id),
            )
        )
    return CoffeeSale(
        id=sale_id,
        machine_id=machine_id,
        selection_id=recipe.selection_id,
        quantity=sold,
        occurred_at=occurred_at,
        consumptions=tuple(consumptions),
    )


def total_snack_consumption(sales: list[SnackSale], *, slot_id: SlotId) -> int:
    return sum(sale.quantity.value for sale in sales if sale.slot_id == slot_id)
