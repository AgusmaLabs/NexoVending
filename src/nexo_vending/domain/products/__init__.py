"""Product catalog entities and contracts."""

from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductStatus, ProductUnit
from nexo_vending.domain.products.errors import (
    CrossTenantProductAccessError,
    DuplicateBarcodeError,
    ProductError,
)
from nexo_vending.domain.products.repositories import ProductRepository
from nexo_vending.domain.products.services import ProductLookup
from nexo_vending.domain.products.value_objects import ProductName

__all__ = [
    "CrossTenantProductAccessError",
    "DuplicateBarcodeError",
    "Product",
    "ProductError",
    "ProductLookup",
    "ProductName",
    "ProductRepository",
    "ProductStatus",
    "ProductUnit",
]
