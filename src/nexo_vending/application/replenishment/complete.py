"""Complete replenishment and emit inventory ledger movements atomically."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import InventoryMovementId, ReplenishmentId, TenantId
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository
from nexo_vending.domain.replenishment.entities import Replenishment, ReplenishmentLine
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class CompleteReplenishmentCommand:
    replenishment_id: ReplenishmentId
    tenant_id: TenantId
    completed_at: datetime


def movement_idempotency_key_for_line(replenishment: Replenishment, line: ReplenishmentLine) -> str:
    return f"{replenishment.idempotency_key}:line:{line.id.value}"


def deferred_resolve_idempotency_key(
    replenishment: Replenishment, line: ReplenishmentLine
) -> str:
    return f"{replenishment.idempotency_key}:line:{line.id.value}:resolve"


class CompleteReplenishment:
    """Complete visit and record movements only for RESOLVED lines."""

    def __init__(
        self,
        replenishments: ReplenishmentRepository,
        inventory: InventoryRepository,
    ) -> None:
        self._replenishments = replenishments
        self._inventory = inventory

    async def execute(self, command: CompleteReplenishmentCommand) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None or replenishment.tenant_id != command.tenant_id:
            raise DomainError("replenishment not found")

        if replenishment.status == ReplenishmentStatus.COMPLETED:
            return replenishment

        for line in replenishment.lines:
            if not line.is_resolved or line.product_id is None:
                continue
            abs_qty = line.quantity.absolute
            slot_location = InventoryLocation.machine_slot(
                replenishment.machine_id,
                line.machine_position_id,
            )
            replenisher_location = InventoryLocation.replenisher(replenishment.operator_id)
            key = movement_idempotency_key_for_line(replenishment, line)
            existing = await self._inventory.find_by_idempotency_key(
                replenishment.tenant_id,
                key,
            )
            if existing is not None:
                continue

            if line.quantity.is_load:
                movement = InventoryMovement(
                    id=InventoryMovementId.new(),
                    tenant_id=replenishment.tenant_id,
                    product_id=line.product_id,
                    quantity=Quantity(abs_qty),
                    movement_type=InventoryMovementType.REPLENISHMENT,
                    reference_type=InventoryReferenceType.REPLENISHMENT,
                    reference_id=str(replenishment.id.value),
                    occurred_at=line.occurred_at,
                    actor_id=replenishment.operator_id,
                    source_location=replenisher_location,
                    destination_location=slot_location,
                    idempotency_key=key,
                )
            else:
                movement = InventoryMovement(
                    id=InventoryMovementId.new(),
                    tenant_id=replenishment.tenant_id,
                    product_id=line.product_id,
                    quantity=Quantity(abs_qty),
                    movement_type=InventoryMovementType.SLOT_REMOVAL,
                    reference_type=InventoryReferenceType.REPLENISHMENT,
                    reference_id=str(replenishment.id.value),
                    occurred_at=line.occurred_at,
                    actor_id=replenishment.operator_id,
                    source_location=slot_location,
                    destination_location=replenisher_location,
                    idempotency_key=key,
                )
            await self._inventory.record_movement(movement)

        replenishment.complete(completed_at=command.completed_at)
        await self._replenishments.save(replenishment)
        return replenishment
