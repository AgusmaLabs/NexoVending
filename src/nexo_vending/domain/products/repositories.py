from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product


class ProductRepository(Protocol):
    async def get(self, product_id: ProductId) -> Product | None: ...

    async def find_by_barcode(self, barcode: Barcode) -> Product | None: ...

    async def save(self, product: Product) -> None: ...
