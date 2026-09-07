from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import MachineId, ReplenishmentId, UserId
from nexo_vending.domain.common.value_objects import GeoLocation
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class StartReplenishmentCommand:
    operator_id: UserId
    machine_id: MachineId
    started_at: datetime
    location: GeoLocation
    idempotency_key: str


class StartReplenishment:
    def __init__(
        self,
        machines: MachineRepository,
        replenishments: ReplenishmentRepository,
    ) -> None:
        self._machines = machines
        self._replenishments = replenishments

    async def execute(self, command: StartReplenishmentCommand) -> Replenishment:
        existing = await self._replenishments.find_by_idempotency_key(
            command.idempotency_key
        )
        if existing is not None:
            return existing

        machine = await self._machines.get(command.machine_id)
        if machine is None:
            raise DomainError("machine not found")

        replenishment = Replenishment.start(
            replenishment_id=ReplenishmentId.new(),
            operator_id=command.operator_id,
            machine=machine,
            started_at=command.started_at,
            location=command.location,
            idempotency_key=command.idempotency_key,
        )
        await self._replenishments.save(replenishment)
        return replenishment
