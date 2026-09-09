"""Machine configuration application use cases."""

from nexo_vending.application.machines.activate_machine import ActivateMachine
from nexo_vending.application.machines.add_machine_slot import AddMachineSlot
from nexo_vending.application.machines.change_slot_capacity import ChangeSlotCapacity
from nexo_vending.application.machines.create_machine import CreateMachine
from nexo_vending.application.machines.deactivate_machine import DeactivateMachine
from nexo_vending.application.machines.get_machine import (
    FindMachineByCode,
    GetMachine,
    ListMachineSlots,
)
from nexo_vending.application.machines.put_machine_in_maintenance import (
    PutMachineInMaintenance,
)
from nexo_vending.application.machines.set_preferred_product import (
    ClearPreferredProduct,
    SetPreferredProduct,
)
from nexo_vending.application.machines.set_slot_selling_price import SetSlotSellingPrice
from nexo_vending.application.machines.slot_lifecycle import (
    ActivateMachineSlot,
    DeactivateMachineSlot,
)
from nexo_vending.application.machines.update_machine import UpdateMachine

__all__ = [
    "ActivateMachine",
    "ActivateMachineSlot",
    "AddMachineSlot",
    "ChangeSlotCapacity",
    "ClearPreferredProduct",
    "CreateMachine",
    "DeactivateMachine",
    "DeactivateMachineSlot",
    "FindMachineByCode",
    "GetMachine",
    "ListMachineSlots",
    "PutMachineInMaintenance",
    "SetPreferredProduct",
    "SetSlotSellingPrice",
    "UpdateMachine",
]
