from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import ProductId, UserId
from nexo_vending.domain.common.value_objects import Quantity


class InventoryAvailability(Protocol):
    """Whether an operator has enough stock of a product for a quantity."""

    async def is_available(
        self,
        operator_id: UserId,
        product_id: ProductId,
        quantity: Quantity,
    ) -> bool: ...
