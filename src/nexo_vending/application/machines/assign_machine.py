"""Assign a replenisher to a machine (admin / provisioning)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.policies import can_manage_machines
from nexo_vending.domain.machines.assignment import MachineAssignment
from nexo_vending.domain.machines.assignment_repository import MachineAssignmentRepository
from nexo_vending.domain.machines.errors import MachineAccessDeniedError, MachineError
from nexo_vending.domain.machines.repositories import MachineRepository


@dataclass(frozen=True, slots=True)
class AssignMachineCommand:
    context: RequestContext
    acting_operator: Operator
    replenisher_id: OperatorId
    machine_id: MachineId
    valid_from: datetime
    valid_until: datetime | None = None


class AssignMachineToReplenisher:
    def __init__(
        self,
        machines: MachineRepository,
        assignments: MachineAssignmentRepository,
    ) -> None:
        self._machines = machines
        self._assignments = assignments

    async def execute(self, command: AssignMachineCommand) -> MachineAssignment:
        if not can_manage_machines(command.acting_operator):
            raise MachineAccessDeniedError("only admins can assign machines")
        tenant_id = TenantId.from_raw(command.context.tenant_id)
        machine = await self._machines.get(command.machine_id)
        if machine is None or machine.tenant_id != tenant_id:
            raise MachineError("machine not found")
        assignment = MachineAssignment.create(
            tenant_id=tenant_id,
            replenisher_id=command.replenisher_id,
            machine_id=command.machine_id,
            valid_from=command.valid_from,
            valid_until=command.valid_until,
        )
        await self._assignments.save(assignment)
        return assignment
