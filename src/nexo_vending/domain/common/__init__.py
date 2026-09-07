"""Shared domain primitives: errors, identifiers, value objects."""

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    MachineId,
    ProductId,
    ReplenishmentId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation, Quantity

__all__ = [
    "Barcode",
    "DomainError",
    "GeoLocation",
    "InventoryMovementId",
    "MachineId",
    "ProductId",
    "Quantity",
    "ReplenishmentId",
    "UserId",
]
