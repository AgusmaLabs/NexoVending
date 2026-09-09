from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_catalog
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductUnit
from nexo_vending.domain.products.errors import (
    CrossTenantProductAccessError,
    ProductError,
)
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class UpdateProductCommand:
    context: RequestContext
    acting_operator: Operator
    product_id: ProductId
    name: str
    description: str | None
    brand: str | None
    category: str | None
    unit: ProductUnit
    low_stock_threshold: int


class UpdateProduct:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(self, command: UpdateProductCommand) -> Product:
        if not can_manage_catalog(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage catalog")

        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")

        product = await self._products.get(command.product_id)
        if product is None:
            raise ProductError("product not found")
        if product.tenant_id != tenant_id:
            raise CrossTenantProductAccessError("cannot update product from another tenant")

        product.update_details(
            name=command.name,
            description=command.description,
            brand=command.brand,
            category=command.category,
            unit=command.unit,
            low_stock_threshold=command.low_stock_threshold,
        )
        await self._products.save(product)
        return product
