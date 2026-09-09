"""Product catalog domain errors."""

from nexo_vending.domain.common.errors import DomainError


class ProductError(DomainError):
    pass


class DuplicateBarcodeError(ProductError):
    pass


class InvalidProductStateError(ProductError):
    pass


class InvalidProductNameError(ProductError):
    pass


class CrossTenantProductAccessError(ProductError):
    pass
