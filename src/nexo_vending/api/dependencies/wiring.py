"""Composition-root helpers for HTTP: Session → use cases (not routers)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from nexo_platform.idempotency import IdempotencyKey, IdempotencyService
from nexo_platform.tenant import RequestContext
from sqlalchemy.orm import Session

from nexo_vending.application.inventory.assign import (
    AdjustInventory,
    AssignInventory,
    GetInventoryBalance,
    RecordLoss,
    ReturnInventory,
)
from nexo_vending.application.inventory.list_movements import ListInventoryMovements
from nexo_vending.application.machines.assign_machine import AssignMachineToReplenisher
from nexo_vending.application.machines.get_machine import GetMachine
from nexo_vending.application.machines.get_machine_slots import GetMachineSlots
from nexo_vending.application.machines.resolve_machine import ResolveMachine
from nexo_vending.application.products.find_product_by_barcode import FindProductByBarcode
from nexo_vending.application.replenishment.add_line import AddReplenishmentLine
from nexo_vending.application.replenishment.cancel import CancelReplenishment
from nexo_vending.application.replenishment.complete import CompleteReplenishment
from nexo_vending.application.replenishment.get import GetReplenishment
from nexo_vending.application.replenishment.list_pending_lines import (
    ListPendingProductResolutions,
)
from nexo_vending.application.replenishment.resolve_line_product import (
    ResolveReplenishmentLineProduct,
)
from nexo_vending.application.replenishment.start import StartReplenishment
from nexo_vending.infrastructure.persistence import VendingPersistence, transactional_uow


@dataclass(slots=True)
class UseCaseFactory:
    """Builds application use cases from ports bound to one Session."""

    persistence: VendingPersistence

    @classmethod
    def from_session(cls, session: Session) -> UseCaseFactory:
        return cls(VendingPersistence.for_session(session))

    def start_replenishment(self) -> StartReplenishment:
        return StartReplenishment(
            self.persistence.machines,
            self.persistence.replenishments,
            self.persistence.assignments,
        )

    def get_replenishment(self) -> GetReplenishment:
        return GetReplenishment(self.persistence.replenishments)

    def add_replenishment_line(self) -> AddReplenishmentLine:
        return AddReplenishmentLine(
            self.persistence.replenishments,
            self.persistence.machines,
            self.persistence.products,
            self.persistence.inventory,
            self.persistence.products,
        )

    def complete_replenishment(self) -> CompleteReplenishment:
        return CompleteReplenishment(
            self.persistence.replenishments,
            self.persistence.inventory,
        )

    def cancel_replenishment(self) -> CancelReplenishment:
        return CancelReplenishment(self.persistence.replenishments)

    def resolve_replenishment_line_product(self) -> ResolveReplenishmentLineProduct:
        return ResolveReplenishmentLineProduct(
            self.persistence.replenishments,
            self.persistence.products,
            self.persistence.inventory,
        )

    def list_pending_product_resolutions(self) -> ListPendingProductResolutions:
        return ListPendingProductResolutions(self.persistence.replenishments)

    def assign_inventory(self) -> AssignInventory:
        return AssignInventory(self.persistence.inventory)

    def return_inventory(self) -> ReturnInventory:
        return ReturnInventory(self.persistence.inventory)

    def adjust_inventory(self) -> AdjustInventory:
        return AdjustInventory(self.persistence.inventory)

    def record_loss(self) -> RecordLoss:
        return RecordLoss(self.persistence.inventory)

    def get_inventory_balance(self) -> GetInventoryBalance:
        return GetInventoryBalance(self.persistence.inventory)

    def list_inventory_movements(self) -> ListInventoryMovements:
        return ListInventoryMovements(self.persistence.inventory)

    def resolve_machine(self) -> ResolveMachine:
        return ResolveMachine(self.persistence.machines, self.persistence.assignments)

    def get_machine(self) -> GetMachine:
        return GetMachine(self.persistence.machines)

    def get_machine_slots(self) -> GetMachineSlots:
        return GetMachineSlots(
            self.persistence.machines,
            self.persistence.assignments,
            self.persistence.inventory,
        )

    def find_product_by_barcode(self) -> FindProductByBarcode:
        return FindProductByBarcode(self.persistence.products)

    def assign_machine(self) -> AssignMachineToReplenisher:
        return AssignMachineToReplenisher(
            self.persistence.machines,
            self.persistence.assignments,
        )


def request_hash_for(payload: bytes | str) -> str:
    data = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    return sha256(data).hexdigest()


async def run_mutating(
    session: Session,
    *,
    context: RequestContext,
    operation: str,
    idempotency_key: str | None,
    request_hash: str,
    handler: Callable[[UseCaseFactory], Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Execute handler inside Platform UoW; wrap with IdempotencyService when keyed."""

    async with transactional_uow(session) as uow:
        factory = UseCaseFactory.from_session(uow.session)
        if idempotency_key is None or not str(idempotency_key).strip():
            return await handler(factory)

        service = IdempotencyService.for_session(uow.session)
        result = await service.execute(
            context=context,
            key=IdempotencyKey(str(idempotency_key).strip()),
            operation=operation,
            request_hash=request_hash,
            handler=lambda: handler(factory),
        )
        return result.result


async def run_query[T](
    session: Session,
    handler: Callable[[UseCaseFactory], Awaitable[T]],
) -> T:
    factory = UseCaseFactory.from_session(session)
    return await handler(factory)
