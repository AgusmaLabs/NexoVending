"""Domain errors for Vending business invariants."""


class DomainError(Exception):
    """Base error for Vending domain rule violations."""


class InvalidBarcodeError(DomainError):
    pass


class InvalidQuantityError(DomainError):
    pass


class InvalidGeoLocationError(DomainError):
    pass


class InvalidThresholdError(DomainError):
    pass


class InactiveMachineError(DomainError):
    pass


class InvalidMachineError(DomainError):
    pass


class InvalidSlotError(DomainError):
    pass


class InvalidReplenishmentStateError(DomainError):
    pass


class InvalidReplenishmentLineError(DomainError):
    pass


class InsufficientStockError(DomainError):
    pass


class NaiveDateTimeError(DomainError):
    pass


class CapacityExceededError(DomainError):
    pass


class SubstitutionRejectedError(DomainError):
    pass


class InvalidInventoryCountError(DomainError):
    pass


class InvalidMachineInventoryError(DomainError):
    pass


class InvalidSaleError(DomainError):
    pass


class InvalidRecipeError(DomainError):
    pass
