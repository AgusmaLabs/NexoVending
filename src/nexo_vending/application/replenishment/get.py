"""Application queries for replenishment reads."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import ReplenishmentId, TenantId
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class GetReplenishmentQuery:
    replenishment_id: ReplenishmentId
    tenant_id: TenantId


class GetReplenishment:
    def __init__(self, replenishments: ReplenishmentRepository) -> None:
        self._replenishments = replenishments

    async def execute(self, query: GetReplenishmentQuery) -> Replenishment:
        replenishment = await self._replenishments.get(query.replenishment_id)
        if replenishment is None or replenishment.tenant_id != query.tenant_id:
            raise DomainError("replenishment not found")
        return replenishment
