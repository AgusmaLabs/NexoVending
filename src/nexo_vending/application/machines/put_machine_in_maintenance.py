from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_machines
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.errors import CrossTenantMachineAccessError, MachineError
from nexo_vending.domain.machines.repositories import MachineRepository


@dataclass(frozen=True, slots=True)
class PutMachineInMaintenanceCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId


class PutMachineInMaintenance:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: PutMachineInMaintenanceCommand) -> Machine:
        if not can_manage_machines(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage machines")
        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")
        machine = await self._machines.get(command.machine_id)
        if machine is None:
            raise MachineError("machine not found")
        if machine.tenant_id != tenant_id:
            raise CrossTenantMachineAccessError(
                "cannot put machine from another tenant in maintenance"
            )
        machine.put_in_maintenance()
        await self._machines.save(machine)
        return machine
