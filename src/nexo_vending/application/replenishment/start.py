from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import MachineId, ReplenishmentId
from nexo_vending.domain.common.value_objects import GeoLocation
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.machines.access import MachineAccessPolicy
from nexo_vending.domain.machines.assignment_repository import MachineAssignmentRepository
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class StartReplenishmentCommand:
    operator: Operator
    machine_id: MachineId
    started_at: datetime
    location: GeoLocation
    idempotency_key: str


class StartReplenishment:
    def __init__(
        self,
        machines: MachineRepository,
        replenishments: ReplenishmentRepository,
        assignments: MachineAssignmentRepository,
        *,
        access_policy: MachineAccessPolicy | None = None,
    ) -> None:
        self._machines = machines
        self._replenishments = replenishments
        self._assignments = assignments
        self._access = access_policy or MachineAccessPolicy()

    async def execute(self, command: StartReplenishmentCommand) -> Replenishment:
        machine = await self._machines.get(command.machine_id)
        if machine is None:
            raise DomainError("machine not found")
        if machine.tenant_id != command.operator.tenant_id:
            raise DomainError("machine not found")

        assignment = await self._assignments.find_active(
            tenant_id=command.operator.tenant_id,
            replenisher_id=command.operator.id,
            machine_id=machine.id,
        )
        self._access.ensure_can_operate(
            operator=command.operator,
            machine=machine,
            assignment=assignment,
            at=command.started_at,
        )

        existing = await self._replenishments.find_by_idempotency_key(
            machine.tenant_id,
            command.idempotency_key,
        )
        if existing is not None:
            return existing

        replenishment = Replenishment.start(
            replenishment_id=ReplenishmentId.new(),
            operator_id=command.operator.id,
            machine=machine,
            started_at=command.started_at,
            location=command.location,
            idempotency_key=command.idempotency_key,
        )
        await self._replenishments.save(replenishment)
        return replenishment
