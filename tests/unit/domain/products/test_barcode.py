import pytest

from nexo_vending.domain.common.errors import InvalidBarcodeError
from nexo_vending.domain.common.value_objects import Barcode


def test_barcode_rejects_empty() -> None:
    with pytest.raises(InvalidBarcodeError):
        Barcode("")


def test_barcode_rejects_whitespace() -> None:
    with pytest.raises(InvalidBarcodeError):
        Barcode("   ")


def test_barcode_trims_whitespace() -> None:
    assert Barcode("  7801234567890  ").value == "7801234567890"


def test_barcode_normalizes_value() -> None:
    assert Barcode.normalize("  ABC-123  ") == "ABC-123"
    assert Barcode("ABC-123").value == "ABC-123"


def test_barcode_equality() -> None:
    assert Barcode("7801234567890") == Barcode(" 7801234567890 ")


def test_barcode_inequality() -> None:
    assert Barcode("7801234567890") != Barcode("7801234567891")


def test_barcode_rejects_invalid_characters() -> None:
    with pytest.raises(InvalidBarcodeError):
        Barcode("780 123")
