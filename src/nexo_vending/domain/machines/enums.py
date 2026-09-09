from enum import StrEnum


class MachineType(StrEnum):
    SNACK = "SNACK"
    COFFEE = "COFFEE"
    MIXED = "MIXED"


class MachineStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"


class SlotStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
