"""Snack and coffee sales / consumption."""

from nexo_vending.domain.sales.entities import (
    CoffeeSale,
    IngredientConsumption,
    Recipe,
    RecipeIngredient,
    SnackSale,
    register_coffee_sale,
    register_snack_sale,
    total_snack_consumption,
)

__all__ = [
    "CoffeeSale",
    "IngredientConsumption",
    "Recipe",
    "RecipeIngredient",
    "SnackSale",
    "register_coffee_sale",
    "register_snack_sale",
    "total_snack_consumption",
]
