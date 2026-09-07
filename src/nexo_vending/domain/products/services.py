from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product


class ProductLookup(Protocol):
    """Resolve a scanned barcode to a catalog product, if any."""

    async def find_by_barcode(self, barcode: Barcode) -> Product | None: ...
