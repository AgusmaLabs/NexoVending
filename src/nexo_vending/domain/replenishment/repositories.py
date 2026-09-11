from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import MachineId, ReplenishmentId, TenantId
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.pending import PendingProductResolutionItem


class ReplenishmentRepository(Protocol):
    async def get(self, replenishment_id: ReplenishmentId) -> Replenishment | None: ...

    async def find_by_idempotency_key(
        self,
        tenant_id: TenantId,
        idempotency_key: str,
    ) -> Replenishment | None: ...

    async def save(self, replenishment: Replenishment) -> None: ...

    async def list_pending_product_resolutions(
        self,
        tenant_id: TenantId,
        *,
        machine_id: MachineId | None = None,
        replenishment_id: ReplenishmentId | None = None,
    ) -> list[PendingProductResolutionItem]: ...
