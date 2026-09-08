from enum import StrEnum


class OperatorStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class OperatorRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
