from __future__ import annotations

from datetime import datetime

from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus


def can_operator_replenish(operator: Operator, at: datetime) -> bool:
    return (
        operator.status == OperatorStatus.ACTIVE
        and operator.role == OperatorRole.OPERATOR
        and operator.validity_period.is_valid_at(at)
    )


def can_manage_operators(operator: Operator) -> bool:
    return (
        operator.status == OperatorStatus.ACTIVE and operator.role == OperatorRole.ADMIN
    )


def can_manage_inventory(operator: Operator) -> bool:
    return can_manage_operators(operator)


def can_manage_machines(operator: Operator) -> bool:
    return can_manage_operators(operator)


def can_manage_catalog(operator: Operator) -> bool:
    """Catalog administration is an ADMIN capability in V4."""
    return can_manage_operators(operator)
