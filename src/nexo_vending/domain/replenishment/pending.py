"""Read models for replenishment admin queues."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.ids import (
    MachineId,
    ReplenishmentId,
    ReplenishmentLineId,
    SlotId,
)
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus


@dataclass(frozen=True, slots=True)
class PendingProductResolutionItem:
    replenishment_id: ReplenishmentId
    line_id: ReplenishmentLineId
    machine_id: MachineId
    slot_id: SlotId
    quantity: int
    manual_description: str
    barcode_scanned: str | None
    occurred_at: datetime
    product_description_snapshot: str
    visit_status: ReplenishmentStatus
