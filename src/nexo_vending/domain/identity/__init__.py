"""Vending identity: Operator lifecycle and authorization policies."""

from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.errors import IdentityError, InvalidOperatorTransitionError
from nexo_vending.domain.identity.policies import (
    can_manage_inventory,
    can_manage_machines,
    can_manage_operators,
    can_operator_replenish,
)
from nexo_vending.domain.identity.repositories import OperatorRepository
from nexo_vending.domain.identity.value_objects import Email, ValidityPeriod

__all__ = [
    "Email",
    "IdentityError",
    "InvalidOperatorTransitionError",
    "Operator",
    "OperatorRepository",
    "OperatorRole",
    "OperatorStatus",
    "ValidityPeriod",
    "can_manage_inventory",
    "can_manage_machines",
    "can_manage_operators",
    "can_operator_replenish",
]
