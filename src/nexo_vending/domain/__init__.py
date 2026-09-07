"""Vending domain package — pure business model, no infrastructure."""

from nexo_vending.domain import (
    common,
    identity,
    inventory,
    machines,
    products,
    replenishment,
)

__all__ = [
    "common",
    "identity",
    "inventory",
    "machines",
    "products",
    "replenishment",
]
