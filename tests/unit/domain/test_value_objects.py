from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import (
    InvalidBarcodeError,
    InvalidGeoLocationError,
    InvalidQuantityError,
    NaiveDateTimeError,
)
from nexo_vending.domain.common.value_objects import Barcode, GeoLocation, Quantity, require_aware


def test_barcode_normalization() -> None:
    assert Barcode("  123456  ").value == "123456"
    assert Barcode("123456") == Barcode("123456")


def test_barcode_rejects_empty() -> None:
    with pytest.raises(InvalidBarcodeError):
        Barcode("   ")


def test_quantity_must_be_positive() -> None:
    with pytest.raises(InvalidQuantityError):
        Quantity(0)
    with pytest.raises(InvalidQuantityError):
        Quantity(-1)
    assert Quantity(1).value == 1


def test_geo_location_bounds() -> None:
    loc = GeoLocation(latitude=-33.4, longitude=-70.6, accuracy=5.0)
    assert loc.accuracy == 5.0
    with pytest.raises(InvalidGeoLocationError):
        GeoLocation(latitude=100, longitude=0, accuracy=1)
    with pytest.raises(InvalidGeoLocationError):
        GeoLocation(latitude=0, longitude=200, accuracy=1)
    with pytest.raises(InvalidGeoLocationError):
        GeoLocation(latitude=0, longitude=0, accuracy=-0.1)


def test_require_aware_rejects_naive() -> None:
    with pytest.raises(NaiveDateTimeError):
        require_aware(datetime(2026, 1, 1), field_name="started_at")
    aware = datetime(2026, 1, 1, tzinfo=UTC)
    assert require_aware(aware) is aware
