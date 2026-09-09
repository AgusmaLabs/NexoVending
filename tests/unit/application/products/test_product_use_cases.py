from __future__ import annotations

import asyncio
from datetime import UTC, datetime

import pytest
from nexo_platform.identity.authentication import Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.application.products.activate_product import (
    ActivateProduct,
    ActivateProductCommand,
)
from nexo_vending.application.products.create_product import (
    CreateProduct,
    CreateProductCommand,
)
from nexo_vending.application.products.deactivate_product import (
    DeactivateProduct,
    DeactivateProductCommand,
)
from nexo_vending.application.products.find_product_by_barcode import (
    FindProductByBarcode,
    FindProductByBarcodeQuery,
)
from nexo_vending.application.products.update_product import (
    UpdateProduct,
    UpdateProductCommand,
)
from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.products.enums import ProductStatus, ProductUnit
from nexo_vending.domain.products.errors import (
    CrossTenantProductAccessError,
    DuplicateBarcodeError,
)
from tests.support.fakes import InMemoryProductRepository


def _admin(tenant: str = "tenant-a") -> Operator:
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId(tenant),
        principal=Principal(provider="google", subject="admin-1"),
        role=OperatorRole.ADMIN,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()
    return operator


def _context(tenant: str = "tenant-a") -> RequestContext:
    return RequestContext.from_principal(
        tenant_id=tenant,
        principal=Principal(provider="google", subject="admin-1"),
    )


def test_create_product() -> None:
    asyncio.run(_test_create_product())


async def _test_create_product() -> None:
    repo = InMemoryProductRepository()
    product = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            barcode="7801234567890",
            name="Cola",
            category="Bebidas",
            unit=ProductUnit.CAN,
        )
    )
    assert product.status == ProductStatus.ACTIVE
    assert product.tenant_id.value == "tenant-a"
    assert product.barcode.value == "7801234567890"


def test_create_product_rejects_duplicate_barcode() -> None:
    asyncio.run(_test_create_product_rejects_duplicate_barcode())


async def _test_create_product_rejects_duplicate_barcode() -> None:
    repo = InMemoryProductRepository()
    cmd = CreateProductCommand(
        context=_context(),
        acting_operator=_admin(),
        barcode="111",
        name="A",
    )
    await CreateProduct(repo).execute(cmd)
    with pytest.raises(DuplicateBarcodeError):
        await CreateProduct(repo).execute(
            CreateProductCommand(
                context=_context(),
                acting_operator=_admin(),
                barcode="111",
                name="B",
            )
        )


def test_create_product_uses_context_tenant() -> None:
    asyncio.run(_test_create_product_uses_context_tenant())


async def _test_create_product_uses_context_tenant() -> None:
    repo = InMemoryProductRepository()
    product = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context("tenant-b"),
            acting_operator=_admin("tenant-b"),
            barcode="222",
            name="Snack",
        )
    )
    assert product.tenant_id.value == "tenant-b"


def test_create_product_uses_authenticated_tenant() -> None:
    asyncio.run(_test_create_product_rejects_claimed_tenant_override())


async def _test_create_product_rejects_claimed_tenant_override() -> None:
    repo = InMemoryProductRepository()
    with pytest.raises(OperatorAuthorizationError, match="cannot override tenant"):
        await CreateProduct(repo).execute(
            CreateProductCommand(
                context=_context("tenant-a"),
                acting_operator=_admin("tenant-a"),
                barcode="333",
                name="X",
                claimed_tenant_id="tenant-b",
            )
        )


def test_update_product() -> None:
    asyncio.run(_test_update_product())


async def _test_update_product() -> None:
    repo = InMemoryProductRepository()
    created = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            barcode="444",
            name="Old",
        )
    )
    updated = await UpdateProduct(repo).execute(
        UpdateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            product_id=created.id,
            name="New",
            description="desc",
            brand="Brand",
            category="Snacks",
            unit=ProductUnit.PACKAGE,
            low_stock_threshold=5,
        )
    )
    assert updated.display_name == "New"
    assert updated.low_stock_threshold == 5
    assert updated.id == created.id
    assert updated.tenant_id == created.tenant_id


def test_update_product_preserves_identity() -> None:
    asyncio.run(_test_update_product())


def test_update_product_rejects_cross_tenant_product() -> None:
    asyncio.run(_test_update_product_rejects_cross_tenant_product())


async def _test_update_product_rejects_cross_tenant_product() -> None:
    repo = InMemoryProductRepository()
    created = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context("tenant-a"),
            acting_operator=_admin("tenant-a"),
            barcode="555",
            name="A",
        )
    )
    with pytest.raises(CrossTenantProductAccessError):
        await UpdateProduct(repo).execute(
            UpdateProductCommand(
                context=_context("tenant-b"),
                acting_operator=_admin("tenant-b"),
                product_id=created.id,
                name="Hack",
                description=None,
                brand=None,
                category=None,
                unit=ProductUnit.UNIT,
                low_stock_threshold=0,
            )
        )


def test_activate_product() -> None:
    asyncio.run(_test_activate_product())


async def _test_activate_product() -> None:
    repo = InMemoryProductRepository()
    created = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            barcode="666",
            name="A",
        )
    )
    await DeactivateProduct(repo).execute(
        DeactivateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            product_id=created.id,
        )
    )
    activated = await ActivateProduct(repo).execute(
        ActivateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            product_id=created.id,
        )
    )
    assert activated.status == ProductStatus.ACTIVE


def test_deactivate_product() -> None:
    asyncio.run(_test_deactivate_product())


async def _test_deactivate_product() -> None:
    repo = InMemoryProductRepository()
    created = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            barcode="777",
            name="A",
        )
    )
    deactivated = await DeactivateProduct(repo).execute(
        DeactivateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            product_id=created.id,
        )
    )
    assert deactivated.status == ProductStatus.INACTIVE


def test_deactivate_product_cannot_cross_tenant() -> None:
    asyncio.run(_test_deactivate_product_cannot_cross_tenant())


async def _test_deactivate_product_cannot_cross_tenant() -> None:
    repo = InMemoryProductRepository()
    created = await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context("tenant-a"),
            acting_operator=_admin("tenant-a"),
            barcode="888",
            name="A",
        )
    )
    with pytest.raises(CrossTenantProductAccessError):
        await DeactivateProduct(repo).execute(
            DeactivateProductCommand(
                context=_context("tenant-b"),
                acting_operator=_admin("tenant-b"),
                product_id=created.id,
            )
        )


def test_find_product_by_barcode() -> None:
    asyncio.run(_test_find_product_by_barcode())


async def _test_find_product_by_barcode() -> None:
    repo = InMemoryProductRepository()
    await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context(),
            acting_operator=_admin(),
            barcode="999",
            name="Found",
        )
    )
    found = await FindProductByBarcode(repo).execute(
        FindProductByBarcodeQuery(context=_context(), barcode="999")
    )
    assert found is not None
    assert found.display_name == "Found"


def test_find_product_by_barcode_returns_none() -> None:
    asyncio.run(_test_find_product_by_barcode_returns_none())


async def _test_find_product_by_barcode_returns_none() -> None:
    repo = InMemoryProductRepository()
    found = await FindProductByBarcode(repo).execute(
        FindProductByBarcodeQuery(context=_context(), barcode="000")
    )
    assert found is None


def test_find_product_by_barcode_is_tenant_scoped() -> None:
    asyncio.run(_test_find_product_by_barcode_is_tenant_scoped())


async def _test_find_product_by_barcode_is_tenant_scoped() -> None:
    repo = InMemoryProductRepository()
    await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context("tenant-a"),
            acting_operator=_admin("tenant-a"),
            barcode="1010",
            name="A",
        )
    )
    await CreateProduct(repo).execute(
        CreateProductCommand(
            context=_context("tenant-b"),
            acting_operator=_admin("tenant-b"),
            barcode="1010",
            name="B",
        )
    )
    found = await FindProductByBarcode(repo).execute(
        FindProductByBarcodeQuery(context=_context("tenant-b"), barcode="1010")
    )
    assert found is not None
    assert found.display_name == "B"
    assert found.tenant_id.value == "tenant-b"


def test_lookup_cannot_cross_tenant() -> None:
    asyncio.run(_test_lookup_cannot_cross_tenant_claim())


async def _test_lookup_cannot_cross_tenant_claim() -> None:
    repo = InMemoryProductRepository()
    with pytest.raises(OperatorAuthorizationError, match="cannot override tenant"):
        await FindProductByBarcode(repo).execute(
            FindProductByBarcodeQuery(
                context=_context("tenant-a"),
                barcode="1010",
                claimed_tenant_id="tenant-b",
            )
        )
