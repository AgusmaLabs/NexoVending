from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexo_platform.tenant import RequestContext

from nexo_vending.application.machines.add_machine_slot import _load_managed_machine
from nexo_vending.domain.common.ids import MachineId, SlotId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.machines.entities import MachineSlot
from nexo_vending.domain.machines.repositories import MachineRepository


@dataclass(frozen=True, slots=True)
class SetSlotSellingPriceCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId
    slot_id: SlotId
    amount: Decimal
    currency: str = "CLP"


class SetSlotSellingPrice:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: SetSlotSellingPriceCommand) -> MachineSlot:
        machine = await _load_managed_machine(
            self._machines, command.context, command.acting_operator, command.machine_id
        )
        slot = machine.set_slot_selling_price(
            command.slot_id,
            command.amount,
            currency=command.currency,
        )
        await self._machines.save(machine)
        return slot
