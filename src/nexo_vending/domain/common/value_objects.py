from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import (
    InvalidBarcodeError,
    InvalidGeoLocationError,
    InvalidQuantityError,
    NaiveDateTimeError,
)

_MAX_BARCODE_LENGTH = 64
# Pragmatic scannable identifiers (EAN/UPC/Code128-like), not a full standards engine.
_BARCODE_CHARS = re.compile(r"^[A-Za-z0-9\-._]+$")


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
        if not _BARCODE_CHARS.match(normalized):
            raise InvalidBarcodeError("barcode contains invalid characters")
        object.__setattr__(self, "value", normalized)

    @staticmethod
    def normalize(raw: str) -> str:
        return raw.strip()


@dataclass(frozen=True, slots=True)
class Quantity:
    """Strictly positive quantity (stock magnitudes, count amounts)."""

    value: int

    def __post_init__(self) -> None:
        if self.value <= 0:
            raise InvalidQuantityError("quantity must be > 0")


@dataclass(frozen=True, slots=True)
class SignedQuantity:
    """Non-zero signed quantity for load (+) / unload (-) replenishment lines."""

    value: int

    def __post_init__(self) -> None:
        if self.value == 0:
            raise InvalidQuantityError("quantity must not be 0")

    @property
    def absolute(self) -> int:
        return abs(self.value)

    @property
    def is_load(self) -> bool:
        return self.value > 0

    @property
    def is_unload(self) -> bool:
        return self.value < 0


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
