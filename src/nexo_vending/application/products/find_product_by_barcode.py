from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class FindProductByBarcodeQuery:
    context: RequestContext
    barcode: str
    claimed_tenant_id: str | None = None


class FindProductByBarcode:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(self, query: FindProductByBarcodeQuery) -> Product | None:
        tenant_id = TenantId.from_raw(query.context.tenant_id)
        if query.claimed_tenant_id is not None:
            claimed = str(query.claimed_tenant_id).strip()
            if claimed != tenant_id.value:
                raise OperatorAuthorizationError("client cannot override tenant_id")

        barcode = Barcode(query.barcode)
        return await self._products.find_by_barcode(tenant_id, barcode)
