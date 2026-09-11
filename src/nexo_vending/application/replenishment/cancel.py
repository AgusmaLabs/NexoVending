from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import ReplenishmentId, TenantId
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class CancelReplenishmentCommand:
    replenishment_id: ReplenishmentId
    tenant_id: TenantId
    cancelled_at: datetime | None = None


class CancelReplenishment:
    def __init__(self, replenishments: ReplenishmentRepository) -> None:
        self._replenishments = replenishments

    async def execute(self, command: CancelReplenishmentCommand) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None or replenishment.tenant_id != command.tenant_id:
            raise DomainError("replenishment not found")
        replenishment.cancel(cancelled_at=command.cancelled_at)
        await self._replenishments.save(replenishment)
        return replenishment
