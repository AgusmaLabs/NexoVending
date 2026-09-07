"""Machine and slot entities and contracts."""

from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.repositories import MachineRepository

__all__ = ["Machine", "MachineRepository", "MachineSlot", "MachineType"]
