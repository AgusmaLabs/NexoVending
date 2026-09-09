from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.application.machines.add_machine_slot import _load_managed_machine
from nexo_vending.domain.common.ids import MachineId, ProductId, SlotId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.machines.entities import MachineSlot
from nexo_vending.domain.machines.errors import MachineError
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.products.enums import ProductStatus
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class SetPreferredProductCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId
    slot_id: SlotId
    product_id: ProductId


class SetPreferredProduct:
    def __init__(
        self,
        machines: MachineRepository,
        products: ProductRepository,
    ) -> None:
        self._machines = machines
        self._products = products

    async def execute(self, command: SetPreferredProductCommand) -> MachineSlot:
        machine = await _load_managed_machine(
            self._machines, command.context, command.acting_operator, command.machine_id
        )
        product = await self._products.get(command.product_id)
        if product is None:
            raise MachineError("preferred product not found")
        if product.tenant_id != machine.tenant_id:
            raise MachineError("preferred product must belong to the same tenant")
        if product.status != ProductStatus.ACTIVE:
            raise MachineError("preferred product must be active")

        slot = machine.set_preferred_product(command.slot_id, command.product_id)
        await self._machines.save(machine)
        return slot


@dataclass(frozen=True, slots=True)
class ClearPreferredProductCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId
    slot_id: SlotId


class ClearPreferredProduct:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: ClearPreferredProductCommand) -> MachineSlot:
        machine = await _load_managed_machine(
            self._machines, command.context, command.acting_operator, command.machine_id
        )
        slot = machine.clear_preferred_product(command.slot_id)
        await self._machines.save(machine)
        return slot
