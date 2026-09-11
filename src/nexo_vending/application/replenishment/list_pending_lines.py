"""Admin query: pending product resolutions on replenishment lines."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.ids import MachineId, ReplenishmentId, TenantId
from nexo_vending.domain.replenishment.pending import PendingProductResolutionItem
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class ListPendingProductResolutionsQuery:
    tenant_id: TenantId
    machine_id: MachineId | None = None
    replenishment_id: ReplenishmentId | None = None


class ListPendingProductResolutions:
    def __init__(self, replenishments: ReplenishmentRepository) -> None:
        self._replenishments = replenishments

    async def execute(
        self, query: ListPendingProductResolutionsQuery
    ) -> list[PendingProductResolutionItem]:
        return await self._replenishments.list_pending_product_resolutions(
            query.tenant_id,
            machine_id=query.machine_id,
            replenishment_id=query.replenishment_id,
        )
