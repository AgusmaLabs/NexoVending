from enum import StrEnum


class ReplenishmentStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ReplacementReason(StrEnum):
    OUT_OF_STOCK = "OUT_OF_STOCK"
    SLOT_EMPTY = "SLOT_EMPTY"
    OPERATIONAL_DECISION = "OPERATIONAL_DECISION"
