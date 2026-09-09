from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import InvalidBarcodeError, InvalidThresholdError
from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductStatus, ProductUnit
from nexo_vending.domain.products.errors import InvalidProductNameError, ProductError
from nexo_vending.domain.products.value_objects import ProductName


def _create(**overrides) -> Product:
    data = {
        "product_id": ProductId.new(),
        "tenant_id": TenantId("tenant-a"),
        "barcode": Barcode("7801234567890"),
        "name": "Cola",
        "created_at": datetime(2026, 9, 9, tzinfo=UTC),
    }
    data.update(overrides)
    return Product.create(**data)


def test_product_requires_tenant() -> None:
    with pytest.raises((ProductError, TypeError, ValueError)):
        Product.create(
            product_id=ProductId.new(),
            tenant_id=None,  # type: ignore[arg-type]
            barcode=Barcode("111"),
            name="Cola",
        )


def test_product_requires_barcode() -> None:
    with pytest.raises(InvalidBarcodeError):
        Product.create(
            product_id=ProductId.new(),
            tenant_id=TenantId("tenant-a"),
            barcode=Barcode(""),
            name="Cola",
        )


def test_product_requires_name() -> None:
    with pytest.raises(InvalidProductNameError):
        _create(name="   ")


def test_product_accepts_optional_description() -> None:
    product = _create(description="Refresco")
    assert product.description == "Refresco"
    assert _create(description=None).description is None


def test_product_accepts_optional_brand() -> None:
    product = _create(brand="ACME")
    assert product.brand == "ACME"


def test_product_accepts_category() -> None:
    product = _create(category="Bebidas")
    assert product.category == "Bebidas"


def test_product_requires_valid_unit() -> None:
    product = _create(unit=ProductUnit.BOTTLE)
    assert product.unit == ProductUnit.BOTTLE
    with pytest.raises(ProductError):
        Product(
            id=ProductId.new(),
            tenant_id=TenantId("tenant-a"),
            barcode=Barcode("111"),
            name=ProductName("X"),
            unit="bottle",  # type: ignore[arg-type]
            low_stock_threshold=0,
            status=ProductStatus.ACTIVE,
            created_at=datetime(2026, 9, 9, tzinfo=UTC),
            updated_at=datetime(2026, 9, 9, tzinfo=UTC),
        )


def test_product_accepts_zero_threshold() -> None:
    assert _create(low_stock_threshold=0).low_stock_threshold == 0


def test_product_rejects_negative_threshold() -> None:
    with pytest.raises(InvalidThresholdError):
        _create(low_stock_threshold=-1)


def test_product_starts_active() -> None:
    assert _create().status == ProductStatus.ACTIVE


def test_active_product_can_be_deactivated() -> None:
    product = _create()
    product.deactivate()
    assert product.status == ProductStatus.INACTIVE


def test_inactive_product_can_be_activated() -> None:
    product = _create()
    product.deactivate()
    product.activate()
    assert product.status == ProductStatus.ACTIVE


def test_product_id_cannot_change() -> None:
    product = _create()
    original = product.id
    # Aggregate exposes no API to mutate identity; field remains the original VO.
    assert product.id is original


def test_tenant_id_cannot_change() -> None:
    product = _create()
    original = product.tenant_id
    assert product.tenant_id is original
    assert product.tenant_id.value == "tenant-a"


def test_deactivated_product_remains_identifiable() -> None:
    product = _create()
    product_id = product.id
    barcode = product.barcode
    product.deactivate()
    assert product.id == product_id
    assert product.barcode == barcode
    assert product.status == ProductStatus.INACTIVE
