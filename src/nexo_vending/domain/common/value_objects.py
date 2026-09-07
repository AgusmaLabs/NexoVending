from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import (
    InvalidBarcodeError,
    InvalidGeoLocationError,
    InvalidQuantityError,
    NaiveDateTimeError,
)

_MAX_BARCODE_LENGTH = 64


@dataclass(frozen=True, slots=True)
class Barcode:
    value: str

    def __post_init__(self) -> None:
        normalized = self.normalize(self.value)
        if not normalized:
            raise InvalidBarcodeError("barcode must not be empty")
        if len(normalized) > _MAX_BARCODE_LENGTH:
            raise InvalidBarcodeError(
                f"barcode length must be <= {_MAX_BARCODE_LENGTH}"
            )
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def normalize(raw: str) -> str:
        return raw.strip()


@dataclass(frozen=True, slots=True)
class Quantity:
    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidQuantityError("quantity must be > 0")


@dataclass(frozen=True, slots=True)
class GeoLocation:
    latitude: float
    longitude: float
    accuracy: float

    def __post_init__(self) -> None:
        if not -90.0 <= self.latitude <= 90.0:
            raise InvalidGeoLocationError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise InvalidGeoLocationError("longitude must be between -180 and 180")
        if self.accuracy < 0:
            raise InvalidGeoLocationError("accuracy must be >= 0")


def require_aware(moment: datetime, *, field_name: str = "timestamp") -> datetime:
    if moment.tzinfo is None or moment.utcoffset() is None:
        raise NaiveDateTimeError(f"{field_name} must be timezone-aware")
    return moment
