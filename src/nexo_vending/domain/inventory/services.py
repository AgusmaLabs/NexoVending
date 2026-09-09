from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.locations import InventoryLocation


class InventoryAvailability(Protocol):
    """Whether a custody/machine location has enough stock of a product."""

    async def is_available(
        self,
        location: InventoryLocation,
        product_id: ProductId,
        quantity: Quantity,
    ) -> bool: ...
