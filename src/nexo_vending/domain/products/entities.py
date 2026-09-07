from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.errors import DomainError, InvalidThresholdError
from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.common.value_objects import Barcode


@dataclass(slots=True)
class Product:
    id: ProductId
    barcode: Barcode
    name: str
    description: str = ""
    brand: str = ""
    category: str = ""
    unit: str = "unit"
    low_stock_threshold: int = 0
    active: bool = True

    def __post_init__(self) -> None:
        name = self.name.strip()
        if not name:
            raise DomainError("product name is required")
        if self.low_stock_threshold < 0:
            raise InvalidThresholdError("low_stock_threshold must be >= 0")
        self.name = name
