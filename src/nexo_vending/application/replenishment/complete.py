from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import ReplenishmentId
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class CompleteReplenishmentCommand:
    replenishment_id: ReplenishmentId
    completed_at: datetime


class CompleteReplenishment:
    def __init__(self, replenishments: ReplenishmentRepository) -> None:
        self._replenishments = replenishments

    async def execute(self, command: CompleteReplenishmentCommand) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None:
            raise DomainError("replenishment not found")
        replenishment.complete(completed_at=command.completed_at)
        await self._replenishments.save(replenishment)
        return replenishment
