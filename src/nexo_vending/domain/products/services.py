from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product


class ProductLookup(Protocol):
    """Resolve a scanned barcode to a catalog product within a tenant."""

    async def find_by_barcode(
        self,
        tenant_id: TenantId,
        barcode: Barcode,
    ) -> Product | None: ...
