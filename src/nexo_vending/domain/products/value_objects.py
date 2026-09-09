from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.products.errors import InvalidProductNameError

_MAX_NAME_LENGTH = 200
_MAX_TEXT_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class ProductName:
    value: str

    def __post_init__(self) -> None:
        normalized = self.value.strip()
        if not normalized:
            raise InvalidProductNameError("product name is required")
        if len(normalized) > _MAX_NAME_LENGTH:
            raise InvalidProductNameError(
                f"product name length must be <= {_MAX_NAME_LENGTH}"
            )
        object.__setattr__(self, "value", normalized)


def normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise InvalidProductNameError(f"{field_name} cannot be whitespace-only")
    if len(normalized) > _MAX_TEXT_LENGTH:
        raise InvalidProductNameError(
            f"{field_name} length must be <= {_MAX_TEXT_LENGTH}"
        )
    return normalized
