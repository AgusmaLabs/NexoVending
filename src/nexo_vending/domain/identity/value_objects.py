from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.value_objects import require_aware
from nexo_vending.domain.identity.errors import InvalidEmailError, InvalidValidityPeriodError

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(frozen=True, slots=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip().lower()
        if not normalized:
            raise InvalidEmailError("email must not be empty")
        if not _EMAIL_RE.match(normalized):
            raise InvalidEmailError("email format is invalid")
        object.__setattr__(self, "value", normalized)


@dataclass(frozen=True, slots=True)
class ValidityPeriod:
    """Half-open interval ``[valid_from, valid_until)``."""

    valid_from: datetime
    valid_until: datetime | None = None

    def __post_init__(self) -> None:
        require_aware(self.valid_from, field_name="valid_from")
        if self.valid_until is not None:
            require_aware(self.valid_until, field_name="valid_until")
            if not self.valid_from < self.valid_until:
                raise InvalidValidityPeriodError("valid_from must be < valid_until")

    def is_valid_at(self, timestamp: datetime) -> bool:
        require_aware(timestamp, field_name="timestamp")
        if timestamp < self.valid_from:
            return False
        if self.valid_until is not None and timestamp >= self.valid_until:
            return False
        return True
