import pytest

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidMachineError,
    InvalidSlotError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId
from nexo_vending.domain.common.value_objects import GeoLocation
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineType


def test_machine_requires_code() -> None:
    with pytest.raises(InvalidMachineError):
        Machine(id=MachineId.new(), code=" ", name="Lobby", type=MachineType.SNACK)


def test_machine_type_required() -> None:
    with pytest.raises(InvalidMachineError):
        Machine(id=MachineId.new(), code="VM-1", name="Lobby", type="SNACK")  # type: ignore[arg-type]


def test_inactive_machine() -> None:
    machine = Machine(
        id=MachineId.new(),
        code="VM-1",
        name="Lobby",
        type=MachineType.SNACK,
        active=False,
    )
    with pytest.raises(InactiveMachineError):
        machine.ensure_can_start_replenishment()


def test_machine_location() -> None:
    location = GeoLocation(latitude=-33.0, longitude=-70.0, accuracy=3.0)
    machine = Machine(
        id=MachineId.new(),
        code="VM-1",
        name="Lobby",
        type=MachineType.COFFEE,
        location=location,
        address="Floor 1",
    )
    assert machine.location == location
    assert machine.address == "Floor 1"


def test_slot_number_must_be_positive() -> None:
    with pytest.raises(InvalidSlotError):
        MachineSlot(machine_id=MachineId.new(), slot_number=0, capacity=10)


def test_slot_capacity_must_be_positive() -> None:
    with pytest.raises(InvalidSlotError):
        MachineSlot(machine_id=MachineId.new(), slot_number=1, capacity=0)


def test_snack_machine_accepts_slots() -> None:
    machine_id = MachineId.new()
    machine = Machine(
        id=machine_id,
        code="VM-S",
        name="Snacks",
        type=MachineType.SNACK,
    )
    machine.add_slot(
        MachineSlot(
            machine_id=machine_id,
            slot_number=1,
            product_id=ProductId.new(),
            capacity=12,
        )
    )
    assert machine.has_slot(1)


def test_coffee_machine_does_not_accept_slots() -> None:
    machine_id = MachineId.new()
    machine = Machine(
        id=machine_id,
        code="VM-C",
        name="Coffee",
        type=MachineType.COFFEE,
    )
    with pytest.raises(InvalidSlotError):
        machine.add_slot(MachineSlot(machine_id=machine_id, slot_number=1, capacity=5))
