import asyncio
from datetime import UTC, datetime

from nexo_platform.identity.authentication import Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.application.products.create_product import (
    CreateProduct,
    CreateProductCommand,
)
from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from tests.support.fakes import InMemoryProductRepository


def test_create_product_binds_platform_request_context_tenant() -> None:
    asyncio.run(_test_create_product_binds_platform_request_context_tenant())


async def _test_create_product_binds_platform_request_context_tenant() -> None:
    principal = Principal(provider="google", subject="catalog-admin")
    context = RequestContext.from_principal(tenant_id="tenant-platform", principal=principal)
    assert RequestContext.__module__.startswith("nexo_platform.")
    assert context.tenant_id == "tenant-platform"
    assert context.principal == principal

    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId.from_raw(context.tenant_id),
        principal=principal,
        role=OperatorRole.ADMIN,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()

    product = await CreateProduct(InMemoryProductRepository()).execute(
        CreateProductCommand(
            context=context,
            acting_operator=operator,
            barcode="7809999888777",
            name="From Context",
        )
    )
    assert product.tenant_id.value == str(context.tenant_id)
