"""Machine domain errors."""

from nexo_vending.domain.common.errors import DomainError


class MachineError(DomainError):
    pass


class InvalidMachineCodeError(MachineError):
    pass


class InvalidMachineTransitionError(MachineError):
    pass


class InvalidSlotConfigurationError(MachineError):
    pass


class InvalidSellingPriceError(MachineError):
    pass


class DuplicateMachineCodeError(MachineError):
    pass


class CrossTenantMachineAccessError(MachineError):
    pass
