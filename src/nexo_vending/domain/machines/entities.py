from __future__ import annotations

from dataclasses import dataclass, field

from nexo_vending.domain.common.errors import (
    DomainError,
    InactiveMachineError,
    InvalidMachineError,
    InvalidSlotError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId
from nexo_vending.domain.common.value_objects import GeoLocation
from nexo_vending.domain.machines.enums import MachineType


@dataclass(slots=True)
class MachineSlot:
    machine_id: MachineId
    slot_number: int
    product_id: ProductId | None = None
    capacity: int = 1
    active: bool = True

    def __post_init__(self) -> None:
        if self.slot_number <= 0:
            raise InvalidSlotError("slot_number must be > 0")
        if self.capacity <= 0:
            raise InvalidSlotError("capacity must be > 0")


@dataclass(slots=True)
class Machine:
    id: MachineId
    code: str
    name: str
    type: MachineType
    location: GeoLocation | None = None
    address: str = ""
    active: bool = True
    _slots: list[MachineSlot] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        code = self.code.strip()
        name = self.name.strip()
        if not code:
            raise InvalidMachineError("machine code is required")
        if not name:
            raise InvalidMachineError("machine name is required")
        if not isinstance(self.type, MachineType):
            raise InvalidMachineError("machine type is required")
        self.code = code
        self.name = name
        if self.type == MachineType.COFFEE and self._slots:
            raise InvalidSlotError("coffee machines do not accept slots")

    @property
    def slots(self) -> tuple[MachineSlot, ...]:
        return tuple(self._slots)

    def ensure_can_start_replenishment(self) -> None:
        if not self.active:
            raise InactiveMachineError("inactive machine cannot start replenishment")

    def add_slot(self, slot: MachineSlot) -> None:
        if self.type == MachineType.COFFEE:
            raise InvalidSlotError("coffee machines do not accept slots")
        if slot.machine_id != self.id:
            raise InvalidSlotError("slot machine_id must match machine id")
        if any(existing.slot_number == slot.slot_number for existing in self._slots):
            raise DomainError(f"slot {slot.slot_number} already exists on machine")
        self._slots.append(slot)

    def has_slot(self, slot_number: int) -> bool:
        return any(slot.slot_number == slot_number and slot.active for slot in self._slots)
