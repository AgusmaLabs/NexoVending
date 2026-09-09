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
class ActivateMachineCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId


class ActivateMachine:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: ActivateMachineCommand) -> Machine:
        return await _lifecycle(self._machines, command, "activate")


@dataclass(frozen=True, slots=True)
class DeactivateMachineCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId


class DeactivateMachine:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: DeactivateMachineCommand) -> Machine:
        return await _lifecycle(self._machines, command, "deactivate")


async def _lifecycle(machines: MachineRepository, command, action: str) -> Machine:
    if not can_manage_machines(command.acting_operator):
        raise OperatorAuthorizationError("operator cannot manage machines")
    tenant_id = TenantId.from_raw(command.context.tenant_id)
    if command.acting_operator.tenant_id != tenant_id:
        raise OperatorAuthorizationError("operator tenant mismatch")
    machine = await machines.get(command.machine_id)
    if machine is None:
        raise MachineError("machine not found")
    if machine.tenant_id != tenant_id:
        raise CrossTenantMachineAccessError(
            f"cannot {action} machine from another tenant"
        )
    if action == "activate":
        machine.activate()
    else:
        machine.deactivate()
    await machines.save(machine)
    return machine
