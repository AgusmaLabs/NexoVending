from enum import StrEnum


class InventoryMovementType(StrEnum):
    ASSIGNMENT = "ASSIGNMENT"
    REPLENISHMENT = "REPLENISHMENT"
    RETURN = "RETURN"
    ADJUSTMENT = "ADJUSTMENT"
    LOSS = "LOSS"
