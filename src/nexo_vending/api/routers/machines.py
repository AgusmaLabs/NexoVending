"""Machine HTTP router — resolve / get / slots for replenishment execution."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from nexo_platform.tenant import RequestContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.access import get_observability, require_permission
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.api.dependencies.wiring import run_query
from nexo_vending.api.schemas.machines import MachineOut, MachineSlotOut, MachineSlotsOut
from nexo_vending.application.access_codes import (
    ENTITLEMENT_REPLENISHMENT,
    MACHINE_READ,
    MACHINE_RESOLVE,
)
from nexo_vending.application.machines.get_machine_slots import GetMachineSlotsQuery
from nexo_vending.application.machines.resolve_machine import ResolveMachineQuery
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.identifiers import MachineIdentifier

router = APIRouter(prefix="/machines", tags=["machines"])


def _slot_out(view) -> MachineSlotOut:
    return MachineSlotOut(
        slot_id=view.slot_id,
        slot_number=view.slot_number,
        capacity=view.capacity,
        status=view.status,
        preferred_product_id=view.preferred_product_id,
        selling_price=view.selling_price,
        current_quantity=view.current_quantity,
    )


def _machine_out(machine: Machine, *, slots: list[MachineSlotOut] | None = None) -> dict:
    slot_payload = slots
    if slot_payload is None:
        slot_payload = [
            MachineSlotOut(
                slot_id=str(slot.id.value),
                slot_number=slot.slot_number,
                capacity=slot.capacity,
                status=slot.status.value,
                preferred_product_id=(
                    str(slot.preferred_product_id.value)
                    if slot.preferred_product_id is not None
                    else None
                ),
                selling_price=(
                    str(slot.selling_price.amount) if slot.selling_price is not None else None
                ),
                current_quantity=None,
            )
            for slot in machine.slots
        ]
    return MachineOut(
        machine_id=str(machine.id.value),
        identifier=machine.code.value,
        machine_type=machine.type.value,
        name=machine.name,
        status=machine.status.value,
        slots=slot_payload,
    ).model_dump()


@router.get("/resolve", response_model=MachineOut)
async def resolve_machine(
    request: Request,
    identifier_type: str = Query(...),
    value: str = Query(...),
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(MACHINE_RESOLVE, ENTITLEMENT_REPLENISHMENT)
    ),
) -> dict:
    context, operator = access
    get_observability(request).logger.info("machine.resolve", context=context)
    identifier = MachineIdentifier.from_raw(identifier_type, value)

    async def _handler(factory):
        machine = await factory.resolve_machine().execute(
            ResolveMachineQuery(
                context=context,
                identifier=identifier,
                acting_operator=operator,
            )
        )
        return _machine_out(machine)

    return await run_query(session, _handler)


@router.get("/{machine_id}", response_model=MachineOut)
async def get_machine(
    machine_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(MACHINE_READ, ENTITLEMENT_REPLENISHMENT)
    ),
) -> dict:
    context, operator = access
    get_observability(request).logger.info("machine.read", context=context)

    async def _handler(factory):
        # Operational get still requires assignment via ResolveMachine INTERNAL_ID.
        machine = await factory.resolve_machine().execute(
            ResolveMachineQuery(
                context=context,
                identifier=MachineIdentifier.from_raw("INTERNAL_ID", machine_id),
                acting_operator=operator,
            )
        )
        return _machine_out(machine)

    return await run_query(session, _handler)


@router.get("/{machine_id}/slots", response_model=MachineSlotsOut)
async def get_machine_slots(
    machine_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(MACHINE_READ, ENTITLEMENT_REPLENISHMENT)
    ),
) -> dict:
    context, operator = access
    get_observability(request).logger.info("machine.slots", context=context)

    async def _handler(factory):
        machine, views = await factory.get_machine_slots().execute(
            GetMachineSlotsQuery(
                context=context,
                machine_id=machine_id,
                acting_operator=operator,
            )
        )
        return MachineSlotsOut(
            machine_id=str(machine.id.value),
            slots=[_slot_out(view) for view in views],
        ).model_dump()

    return await run_query(session, _handler)
