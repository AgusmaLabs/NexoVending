from __future__ import annotations

from collections.abc import Iterable

from nexo_vending.domain.common.ids import ProductId, UserId
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.inventory.locations import InventoryLocation


class CustodyInventory:
    """Expected (book) inventory for administrator / replenisher custody."""

    @staticmethod
    def administrator_expected(
        movements: Iterable[InventoryMovement],
        *,
        administrator_id: UserId,
        product_id: ProductId,
    ) -> int:
        return InventoryLedger.expected_quantity(
            movements,
            location=InventoryLocation.administrator(administrator_id),
            product_id=product_id,
        )

    @staticmethod
    def replenisher_expected(
        movements: Iterable[InventoryMovement],
        *,
        replenisher_id: UserId,
        product_id: ProductId,
    ) -> int:
        return InventoryLedger.expected_quantity(
            movements,
            location=InventoryLocation.replenisher(replenisher_id),
            product_id=product_id,
        )
