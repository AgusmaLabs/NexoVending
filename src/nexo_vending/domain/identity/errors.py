"""Identity-specific domain errors."""

from nexo_vending.domain.common.errors import DomainError


class IdentityError(DomainError):
    pass


class InvalidOperatorTransitionError(IdentityError):
    pass


class InvalidEmailError(IdentityError):
    pass


class InvalidValidityPeriodError(IdentityError):
    pass


class OperatorNotFoundError(IdentityError):
    pass


class OperatorAuthorizationError(IdentityError):
    pass
