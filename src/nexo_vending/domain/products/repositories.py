from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product


class ProductRepository(Protocol):
    async def get(self, product_id: ProductId) -> Product | None: ...

    async def save(self, product: Product) -> None: ...

    async def find_by_barcode(
        self,
        tenant_id: TenantId,
        barcode: Barcode,
    ) -> Product | None: ...

    async def list_active(self, tenant_id: TenantId) -> list[Product]: ...
