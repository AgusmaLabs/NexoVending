"""Inventory HTTP router — thin inbound adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from nexo_platform.tenant import RequestContext, TenantContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.access import (
    ensure_can_manage_inventory,
    get_observability,
    require_permission,
)
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.api.dependencies.wiring import request_hash_for, run_mutating, run_query
from nexo_vending.api.location_parse import parse_location
from nexo_vending.api.schemas.inventory import (
    AdjustInventoryRequest,
    AssignInventoryRequest,
    InventoryBalanceOut,
    InventoryMovementsOut,
    RecordLossRequest,
    ReturnInventoryRequest,
)
from nexo_vending.api.serializers import location_to_dict, movement_to_dict
from nexo_vending.application.access_codes import (
    ENTITLEMENT_INVENTORY,
    INVENTORY_ADJUST,
    INVENTORY_ASSIGN,
    INVENTORY_LOSS,
    INVENTORY_READ,
    INVENTORY_RETURN,
)
from nexo_vending.application.inventory.assign import (
    AdjustInventoryCommand,
    AssignInventoryCommand,
    GetInventoryBalanceQuery,
    RecordLossCommand,
    ReturnInventoryCommand,
)
from nexo_vending.application.inventory.list_movements import ListInventoryMovementsQuery
from nexo_vending.domain.common.ids import ProductId, TenantId, UserId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.inventory.locations import InventoryLocation

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _tenant(context: RequestContext) -> TenantId:
    return TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())


def _location_from_query(
    location_type: str,
    holder_id: str,
    position_id: str | None,
) -> InventoryLocation:
    from nexo_vending.api.schemas.inventory import InventoryLocationIn

    return parse_location(
        InventoryLocationIn(
            location_type=location_type,
            holder_id=holder_id,
            position_id=position_id,
        )
    )


@router.post("/assignments", status_code=201)
async def assign_inventory(
    body: AssignInventoryRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_ASSIGN, ENTITLEMENT_INVENTORY)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_manage_inventory(operator)
    get_observability(request).logger.info("inventory.assign.started", context=context)
    raw = body.model_dump_json().encode()

    async def _handler(factory):
        movement = await factory.assign_inventory().execute(
            AssignInventoryCommand(
                tenant_id=_tenant(context),
                product_id=ProductId(UUID(body.product_id)),
                quantity=body.quantity,
                replenisher_id=UserId(UUID(body.replenisher_id)),
                actor_id=operator.id,
                occurred_at=body.occurred_at or datetime.now(UTC),
                reference_id=body.reference_id,
                administrator_id=(
                    UserId(UUID(body.administrator_id)) if body.administrator_id else None
                ),
                idempotency_key=idempotency_key,
            )
        )
        return movement_to_dict(movement)

    return await run_mutating(
        session,
        context=context,
        operation="inventory.assign",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )


@router.post("/returns", status_code=201)
async def return_inventory(
    body: ReturnInventoryRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_RETURN, ENTITLEMENT_INVENTORY)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_manage_inventory(operator)
    raw = body.model_dump_json().encode()

    async def _handler(factory):
        movement = await factory.return_inventory().execute(
            ReturnInventoryCommand(
                tenant_id=_tenant(context),
                product_id=ProductId(UUID(body.product_id)),
                quantity=body.quantity,
                replenisher_id=UserId(UUID(body.replenisher_id)),
                administrator_id=UserId(UUID(body.administrator_id)),
                actor_id=operator.id,
                occurred_at=body.occurred_at or datetime.now(UTC),
                reference_id=body.reference_id,
                idempotency_key=idempotency_key,
            )
        )
        return movement_to_dict(movement)

    return await run_mutating(
        session,
        context=context,
        operation="inventory.return",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )


@router.post("/adjustments", status_code=201)
async def adjust_inventory(
    body: AdjustInventoryRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_ADJUST, ENTITLEMENT_INVENTORY)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_manage_inventory(operator)
    raw = body.model_dump_json().encode()

    async def _handler(factory):
        movement = await factory.adjust_inventory().execute(
            AdjustInventoryCommand(
                tenant_id=_tenant(context),
                product_id=ProductId(UUID(body.product_id)),
                quantity=body.quantity,
                location=parse_location(body.location),
                actor_id=operator.id,
                occurred_at=body.occurred_at or datetime.now(UTC),
                reference_id=body.reference_id,
                as_increase=body.as_increase,
                idempotency_key=idempotency_key,
            )
        )
        return movement_to_dict(movement)

    return await run_mutating(
        session,
        context=context,
        operation="inventory.adjust",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )


@router.post("/losses", status_code=201)
async def record_loss(
    body: RecordLossRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_LOSS, ENTITLEMENT_INVENTORY)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_manage_inventory(operator)
    raw = body.model_dump_json().encode()

    async def _handler(factory):
        movement = await factory.record_loss().execute(
            RecordLossCommand(
                tenant_id=_tenant(context),
                product_id=ProductId(UUID(body.product_id)),
                quantity=body.quantity,
                location=parse_location(body.location),
                actor_id=operator.id,
                occurred_at=body.occurred_at or datetime.now(UTC),
                reference_id=body.reference_id,
                idempotency_key=idempotency_key,
            )
        )
        return movement_to_dict(movement)

    return await run_mutating(
        session,
        context=context,
        operation="inventory.loss",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )


@router.get("/balance", response_model=InventoryBalanceOut)
async def get_inventory_balance(
    request: Request,
    location_type: str = Query(...),
    holder_id: str = Query(...),
    product_id: str = Query(...),
    position_id: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_READ, ENTITLEMENT_INVENTORY)
    ),
) -> dict:
    context, _operator = access
    location = _location_from_query(location_type, holder_id, position_id)
    get_observability(request).logger.info("inventory.balance", context=context)

    async def _handler(factory):
        quantity = await factory.get_inventory_balance().execute(
            GetInventoryBalanceQuery(
                tenant_id=_tenant(context),
                location=location,
                product_id=ProductId(UUID(product_id)),
            )
        )
        return {
            "quantity": quantity,
            "location": location_to_dict(location),
            "product_id": product_id,
        }

    return await run_query(session, _handler)


@router.get("/movements", response_model=InventoryMovementsOut)
async def list_inventory_movements(
    request: Request,
    location_type: str = Query(...),
    holder_id: str = Query(...),
    product_id: str | None = Query(default=None),
    position_id: str | None = Query(default=None),
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(INVENTORY_READ, ENTITLEMENT_INVENTORY)
    ),
) -> dict:
    context, _operator = access
    location = _location_from_query(location_type, holder_id, position_id)
    get_observability(request).logger.info("inventory.movements", context=context)

    async def _handler(factory):
        items = await factory.list_inventory_movements().execute(
            ListInventoryMovementsQuery(
                tenant_id=_tenant(context),
                location=location,
                product_id=ProductId(UUID(product_id)) if product_id else None,
            )
        )
        return {"items": [movement_to_dict(item) for item in items]}

    return await run_query(session, _handler)
