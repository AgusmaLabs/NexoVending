import pytest

from nexo_vending.domain.common.errors import (
    DomainError,
    InvalidBarcodeError,
    InvalidThresholdError,
)
from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.products.entities import Product


def test_product_requires_barcode() -> None:
    with pytest.raises(InvalidBarcodeError):
        Product(id=ProductId.new(), barcode=Barcode(""), name="Cola")


def test_product_requires_name() -> None:
    with pytest.raises(DomainError):
        Product(id=ProductId.new(), barcode=Barcode("111"), name="  ")


def test_invalid_threshold() -> None:
    with pytest.raises(InvalidThresholdError):
        Product(
            id=ProductId.new(),
            barcode=Barcode("111"),
            name="Cola",
            low_stock_threshold=-1,
        )


def test_product_accepts_valid_data() -> None:
    product = Product(
        id=ProductId.new(),
        barcode=Barcode(" 999 "),
        name="  Agua ",
        low_stock_threshold=0,
    )
    assert product.barcode.value == "999"
    assert product.name == "Agua"
