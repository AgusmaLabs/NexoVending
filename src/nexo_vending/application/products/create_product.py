from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_catalog
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductUnit
from nexo_vending.domain.products.errors import DuplicateBarcodeError
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class CreateProductCommand:
    context: RequestContext
    acting_operator: Operator
    barcode: str
    name: str
    description: str | None = None
    brand: str | None = None
    category: str | None = None
    unit: ProductUnit = ProductUnit.UNIT
    low_stock_threshold: int = 0
    # Explicitly ignored — documents that clients cannot override tenant.
    claimed_tenant_id: str | None = None


class CreateProduct:
    def __init__(self, products: ProductRepository) -> None:
        self._products = products

    async def execute(self, command: CreateProductCommand) -> Product:
        if not can_manage_catalog(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage catalog")

        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.claimed_tenant_id is not None:
            claimed = str(command.claimed_tenant_id).strip()
            if claimed != tenant_id.value:
                raise OperatorAuthorizationError("client cannot override tenant_id")

        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")

        barcode = Barcode(command.barcode)
        existing = await self._products.find_by_barcode(tenant_id, barcode)
        if existing is not None:
            raise DuplicateBarcodeError(
                "barcode already exists for an active or inactive product in tenant"
            )

        product = Product.create(
            product_id=ProductId.new(),
            tenant_id=tenant_id,
            barcode=barcode,
            name=command.name,
            description=command.description,
            brand=command.brand,
            category=command.category,
            unit=command.unit,
            low_stock_threshold=command.low_stock_threshold,
        )
        await self._products.save(product)
        return product
