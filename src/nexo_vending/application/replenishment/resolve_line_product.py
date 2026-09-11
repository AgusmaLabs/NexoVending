"""Admin resolve of PENDING_PRODUCT_RESOLUTION replenishment lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.application.replenishment.complete import (
    deferred_resolve_idempotency_key,
    movement_idempotency_key_for_line,
)
from nexo_vending.domain.common.errors import DomainError, InsufficientStockError
from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    ReplenishmentLineId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import Quantity
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository
from nexo_vending.domain.products.repositories import ProductRepository
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class ResolveReplenishmentLineProductCommand:
    tenant_id: TenantId
    replenishment_id: ReplenishmentId
    line_id: ReplenishmentLineId
    product_id: ProductId
    resolved_at: datetime
    actor_operator_id: OperatorId


class ResolveReplenishmentLineProduct:
    """Assign catalog product to a pending line; defer inventory if visit completed.

    Movement rule:
    - resolve while IN_PROGRESS → update line only; Complete writes ``:line:{id}``
    - resolve after COMPLETED → write deferred movement with ``:line:{id}:resolve``
    """

    def __init__(
        self,
        replenishments: ReplenishmentRepository,
        products: ProductRepository,
        inventory: InventoryRepository,
    ) -> None:
        self._replenishments = replenishments
        self._products = products
        self._inventory = inventory

    async def execute(
        self, command: ResolveReplenishmentLineProductCommand
    ) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None or replenishment.tenant_id != command.tenant_id:
            raise DomainError("replenishment not found")

        product = await self._products.get(command.product_id)
        if product is None or product.tenant_id != command.tenant_id:
            raise DomainError("product not found")

        line_before = next(
            (line for line in replenishment.lines if line.id == command.line_id),
            None,
        )
        if line_before is None:
            raise DomainError("line not found")

        # Idempotent short-circuit before stock/mutation side effects.
        if line_before.is_resolved:
            if line_before.product_id == command.product_id:
                return replenishment
            raise DomainError("line already resolved with different product")

        if not line_before.is_pending_product_resolution:
            raise DomainError("line is not pending product resolution")

        write_deferred = replenishment.status == ReplenishmentStatus.COMPLETED
        if write_deferred and line_before.quantity.is_load:
            available = await self._inventory.expected_quantity(
                InventoryLocation.replenisher(replenishment.operator_id),
                product.id,
            )
            if line_before.quantity.absolute > available:
                raise InsufficientStockError(
                    f"insufficient replenisher inventory: "
                    f"need {line_before.quantity.absolute}, have {available}"
                )

        line = replenishment.resolve_line_product(
            line_id=command.line_id,
            product_id=product.id,
            product_description_snapshot=product.display_name,
            resolved_at=command.resolved_at,
            resolved_by_operator_id=command.actor_operator_id,
        )

        if write_deferred and line.product_id is not None:
            resolve_key = deferred_resolve_idempotency_key(replenishment, line)
            complete_key = movement_idempotency_key_for_line(replenishment, line)
            existing = await self._inventory.find_by_idempotency_key(
                replenishment.tenant_id, resolve_key
            )
            if existing is None:
                existing = await self._inventory.find_by_idempotency_key(
                    replenishment.tenant_id, complete_key
                )
            if existing is None:
                abs_qty = line.quantity.absolute
                slot_location = InventoryLocation.machine_slot(
                    replenishment.machine_id,
                    line.machine_position_id,
                )
                replenisher_location = InventoryLocation.replenisher(
                    replenishment.operator_id
                )
                if line.quantity.is_load:
                    movement = InventoryMovement(
                        id=InventoryMovementId.new(),
                        tenant_id=replenishment.tenant_id,
                        product_id=line.product_id,
                        quantity=Quantity(abs_qty),
                        movement_type=InventoryMovementType.REPLENISHMENT,
                        reference_type=InventoryReferenceType.REPLENISHMENT,
                        reference_id=str(replenishment.id.value),
                        occurred_at=command.resolved_at,
                        actor_id=command.actor_operator_id,
                        source_location=replenisher_location,
                        destination_location=slot_location,
                        idempotency_key=resolve_key,
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
                        occurred_at=command.resolved_at,
                        actor_id=command.actor_operator_id,
                        source_location=slot_location,
                        destination_location=replenisher_location,
                        idempotency_key=resolve_key,
                    )
                await self._inventory.record_movement(movement)

        await self._replenishments.save(replenishment)
        return replenishment
