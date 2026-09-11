"""Inventory assignment and adjustment use cases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.application.inventory.register_movement import (
    RegisterInventoryMovement,
    RegisterInventoryMovementCommand,
)
from nexo_vending.domain.common.ids import ProductId, TenantId, UserId
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository


@dataclass(frozen=True, slots=True)
class AssignInventoryCommand:
    tenant_id: TenantId
    product_id: ProductId
    quantity: int
    replenisher_id: UserId
    actor_id: UserId
    occurred_at: datetime
    reference_id: str
    administrator_id: UserId | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class ReturnInventoryCommand:
    tenant_id: TenantId
    product_id: ProductId
    quantity: int
    replenisher_id: UserId
    administrator_id: UserId
    actor_id: UserId
    occurred_at: datetime
    reference_id: str
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class AdjustInventoryCommand:
    tenant_id: TenantId
    product_id: ProductId
    quantity: int
    location: InventoryLocation
    actor_id: UserId
    occurred_at: datetime
    reference_id: str
    as_increase: bool = True
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class RecordLossCommand:
    tenant_id: TenantId
    product_id: ProductId
    quantity: int
    location: InventoryLocation
    actor_id: UserId
    occurred_at: datetime
    reference_id: str
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class GetInventoryBalanceQuery:
    tenant_id: TenantId
    location: InventoryLocation
    product_id: ProductId


class AssignInventory:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._register = RegisterInventoryMovement(inventory)

    async def execute(self, command: AssignInventoryCommand) -> InventoryMovement:
        source = (
            InventoryLocation.administrator(command.administrator_id)
            if command.administrator_id is not None
            else None
        )
        return await self._register.execute(
            RegisterInventoryMovementCommand(
                tenant_id=command.tenant_id,
                product_id=command.product_id,
                quantity=command.quantity,
                movement_type=InventoryMovementType.ASSIGNMENT,
                reference_type=InventoryReferenceType.ASSIGNMENT,
                reference_id=command.reference_id,
                occurred_at=command.occurred_at,
                actor_id=command.actor_id,
                source_location=source,
                destination_location=InventoryLocation.replenisher(command.replenisher_id),
                idempotency_key=command.idempotency_key,
            )
        )


class ReturnInventory:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._register = RegisterInventoryMovement(inventory)

    async def execute(self, command: ReturnInventoryCommand) -> InventoryMovement:
        return await self._register.execute(
            RegisterInventoryMovementCommand(
                tenant_id=command.tenant_id,
                product_id=command.product_id,
                quantity=command.quantity,
                movement_type=InventoryMovementType.RETURN,
                reference_type=InventoryReferenceType.RETURN,
                reference_id=command.reference_id,
                occurred_at=command.occurred_at,
                actor_id=command.actor_id,
                source_location=InventoryLocation.replenisher(command.replenisher_id),
                destination_location=InventoryLocation.administrator(
                    command.administrator_id
                ),
                idempotency_key=command.idempotency_key,
            )
        )


class AdjustInventory:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._register = RegisterInventoryMovement(inventory)

    async def execute(self, command: AdjustInventoryCommand) -> InventoryMovement:
        if command.as_increase:
            source, destination = None, command.location
        else:
            source, destination = command.location, None
        return await self._register.execute(
            RegisterInventoryMovementCommand(
                tenant_id=command.tenant_id,
                product_id=command.product_id,
                quantity=command.quantity,
                movement_type=InventoryMovementType.ADJUSTMENT,
                reference_type=InventoryReferenceType.MANUAL,
                reference_id=command.reference_id,
                occurred_at=command.occurred_at,
                actor_id=command.actor_id,
                source_location=source,
                destination_location=destination,
                idempotency_key=command.idempotency_key,
            )
        )


class RecordLoss:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._register = RegisterInventoryMovement(inventory)

    async def execute(self, command: RecordLossCommand) -> InventoryMovement:
        return await self._register.execute(
            RegisterInventoryMovementCommand(
                tenant_id=command.tenant_id,
                product_id=command.product_id,
                quantity=command.quantity,
                movement_type=InventoryMovementType.LOSS,
                reference_type=InventoryReferenceType.MANUAL,
                reference_id=command.reference_id,
                occurred_at=command.occurred_at,
                actor_id=command.actor_id,
                source_location=command.location,
                destination_location=None,
                idempotency_key=command.idempotency_key,
            )
        )


class GetInventoryBalance:
    def __init__(self, inventory: InventoryRepository) -> None:
        self._inventory = inventory

    async def execute(self, query: GetInventoryBalanceQuery) -> int:
        movements = await self._inventory.list_movements_for_location(
            query.location,
            query.product_id,
        )
        scoped = [m for m in movements if m.tenant_id == query.tenant_id]
        return InventoryLedger.expected_quantity(
            scoped,
            location=query.location,
            product_id=query.product_id,
        )
