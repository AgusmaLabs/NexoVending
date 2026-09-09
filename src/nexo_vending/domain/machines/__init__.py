"""Machine and physical slot configuration."""

from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineStatus, MachineType, SlotStatus
from nexo_vending.domain.machines.errors import (
    CrossTenantMachineAccessError,
    DuplicateMachineCodeError,
    MachineError,
)
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.machines.value_objects import (
    MachineCode,
    MachineLocation,
    SellingPrice,
)

__all__ = [
    "CrossTenantMachineAccessError",
    "DuplicateMachineCodeError",
    "Machine",
    "MachineCode",
    "MachineError",
    "MachineLocation",
    "MachineRepository",
    "MachineSlot",
    "MachineStatus",
    "MachineType",
    "SellingPrice",
    "SlotStatus",
]
