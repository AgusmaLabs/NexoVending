from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexo_vending.domain.common.errors import InvalidGeoLocationError, InvalidMachineError
from nexo_vending.domain.machines.errors import InvalidMachineCodeError, InvalidSellingPriceError

_MAX_CODE_LENGTH = 64


@dataclass(frozen=True, slots=True)
class MachineCode:
    """Operational machine code (future QR reference). Unique per tenant."""

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().upper()
        if not normalized:
            raise InvalidMachineCodeError("machine code is required")
        if len(normalized) > _MAX_CODE_LENGTH:
            raise InvalidMachineCodeError(
                f"machine code length must be <= {_MAX_CODE_LENGTH}"
            )
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class MachineLocation:
    """Configured machine location (not replenishment GPS)."""

    address: str
    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        address = self.address.strip()
        if not address:
            raise InvalidMachineError("machine address is required when location is set")
        if not -90.0 <= self.latitude <= 90.0:
            raise InvalidGeoLocationError("latitude must be between -90 and 90")
        if not -180.0 <= self.longitude <= 180.0:
            raise InvalidGeoLocationError("longitude must be between -180 and 180")
        object.__setattr__(self, "address", address)


@dataclass(frozen=True, slots=True)
class SellingPrice:
    """Configured selling price for a physical slot position."""

    amount: Decimal
    currency: str = "CLP"

    def __post_init__(self) -> None:
        amount = Decimal(self.amount)
        if amount < 0:
            raise InvalidSellingPriceError("selling price must be >= 0")
        currency = self.currency.strip().upper()
        if not currency:
            raise InvalidSellingPriceError("currency is required")
        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)
