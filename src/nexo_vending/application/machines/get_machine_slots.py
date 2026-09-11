"""Operational slot view for replenishment execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nexo_platform.tenant import RequestContext

from nexo_vending.application.machines.resolve_machine import ResolveMachine, ResolveMachineQuery
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository
from nexo_vending.domain.machines.assignment_repository import MachineAssignmentRepository
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.identifiers import MachineIdentifier, MachineIdentifierType
from nexo_vending.domain.machines.repositories import MachineRepository


@dataclass(frozen=True, slots=True)
class OperationalSlotView:
    slot_id: str
    slot_number: int
    capacity: int
    status: str
    preferred_product_id: str | None
    selling_price: str | None
    current_quantity: int | None


@dataclass(frozen=True, slots=True)
class GetMachineSlotsQuery:
    context: RequestContext
    machine_id: str
    acting_operator: Operator
    at: datetime | None = None


class GetMachineSlots:
    """Return slot configuration + current stock for preferred product (if set)."""

    def __init__(
        self,
        machines: MachineRepository,
        assignments: MachineAssignmentRepository,
        inventory: InventoryRepository,
    ) -> None:
        self._resolve = ResolveMachine(machines, assignments)
        self._inventory = inventory

    async def execute(self, query: GetMachineSlotsQuery) -> tuple[Machine, list[OperationalSlotView]]:
        machine = await self._resolve.execute(
            ResolveMachineQuery(
                context=query.context,
                identifier=MachineIdentifier(
                    identifier_type=MachineIdentifierType.INTERNAL_ID,
                    identifier_value=query.machine_id,
                ),
                acting_operator=query.acting_operator,
                at=query.at or datetime.now(UTC),
            )
        )
        views: list[OperationalSlotView] = []
        for slot in machine.slots:
            views.append(await self._to_view(machine, slot))
        return machine, views

    async def _to_view(self, machine: Machine, slot: MachineSlot) -> OperationalSlotView:
        current: int | None = None
        if slot.preferred_product_id is not None:
            location = InventoryLocation.machine_slot(machine.id, slot.id)
            current = await self._inventory.expected_quantity(
                location,
                slot.preferred_product_id,
            )
        price = None
        if slot.selling_price is not None:
            price = str(slot.selling_price.amount)
        preferred: str | None = None
        if slot.preferred_product_id is not None:
            preferred = str(slot.preferred_product_id.value)
        return OperationalSlotView(
            slot_id=str(slot.id.value),
            slot_number=slot.slot_number,
            capacity=slot.capacity,
            status=slot.status.value,
            preferred_product_id=preferred,
            selling_price=price,
            current_quantity=current,
        )
