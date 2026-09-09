from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_catalog
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.errors import (
    CrossTenantProductAccessError,
    DuplicateBarcodeError,
    ProductError,
)
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class ChangeProductBarcodeCommand:
    context: RequestContext
    acting_operator: Operator
    product_id: ProductId
    barcode: str


class ChangeProductBarcode:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(self, command: ChangeProductBarcodeCommand) -> Product:
        if not can_manage_catalog(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage catalog")

        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")

        product = await self._products.get(command.product_id)
        if product is None:
            raise ProductError("product not found")
        if product.tenant_id != tenant_id:
            raise CrossTenantProductAccessError(
                "cannot change barcode of product from another tenant"
            )

        barcode = Barcode(command.barcode)
        existing = await self._products.find_by_barcode(tenant_id, barcode)
        if existing is not None and existing.id != product.id:
            raise DuplicateBarcodeError("barcode already exists within tenant")

        product.change_barcode(barcode)
        await self._products.save(product)
        return product
