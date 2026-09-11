"""Product HTTP router — barcode lookup for replenishment capture."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from nexo_platform.tenant import RequestContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.access import get_observability, require_permission
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.api.dependencies.wiring import run_query
from nexo_vending.api.schemas.products import ProductOut
from nexo_vending.application.access_codes import ENTITLEMENT_REPLENISHMENT, PRODUCT_READ
from nexo_vending.application.products.find_product_by_barcode import FindProductByBarcodeQuery
from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.identity.entities import Operator

router = APIRouter(prefix="/products", tags=["products"])


@router.get("/barcode/{barcode}", response_model=ProductOut)
async def find_product_by_barcode(
    barcode: str,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(PRODUCT_READ, ENTITLEMENT_REPLENISHMENT)
    ),
) -> dict:
    context, _operator = access
    get_observability(request).logger.info("product.barcode.lookup", context=context)

    async def _handler(factory):
        product = await factory.find_product_by_barcode().execute(
            FindProductByBarcodeQuery(context=context, barcode=barcode)
        )
        if product is None:
            raise DomainError("product not found")
        return ProductOut(
            product_id=str(product.id.value),
            barcode=product.barcode.value,
            name=product.name.value,
            status=product.status.value,
            unit=product.unit.value,
        ).model_dump()

    return await run_query(session, _handler)
