"""Replenishment HTTP router — thin inbound adapter."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from nexo_platform.tenant import RequestContext, TenantContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.access import (
    ensure_can_replenish,
    ensure_can_resolve_product,
    get_observability,
    require_permission,
)
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.api.dependencies.wiring import request_hash_for, run_mutating, run_query
from nexo_vending.api.schemas.replenishment import (
    AddReplenishmentLineRequest,
    CancelReplenishmentRequest,
    CompleteReplenishmentRequest,
    CreateReplenishmentRequest,
    PendingProductResolutionsOut,
    ReplenishmentOut,
    ResolveReplenishmentLineProductRequest,
)
from nexo_vending.api.serializers import pending_resolution_to_dict, replenishment_to_dict
from nexo_vending.application.access_codes import (
    ENTITLEMENT_REPLENISHMENT,
    REPLENISHMENT_ADD_LINE,
    REPLENISHMENT_CANCEL,
    REPLENISHMENT_COMPLETE,
    REPLENISHMENT_CREATE,
    REPLENISHMENT_READ,
    REPLENISHMENT_RESOLVE_PRODUCT,
)
from nexo_vending.application.replenishment.add_line import AddReplenishmentLineCommand
from nexo_vending.application.replenishment.cancel import CancelReplenishmentCommand
from nexo_vending.application.replenishment.complete import CompleteReplenishmentCommand
from nexo_vending.application.replenishment.get import GetReplenishmentQuery
from nexo_vending.application.replenishment.list_pending_lines import (
    ListPendingProductResolutionsQuery,
)
from nexo_vending.application.replenishment.resolve_line_product import (
    ResolveReplenishmentLineProductCommand,
)
from nexo_vending.application.replenishment.start import StartReplenishmentCommand
from nexo_vending.domain.common.ids import (
    MachineId,
    ProductId,
    ReplenishmentId,
    ReplenishmentLineId,
    SlotId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import GeoLocation
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.replenishment.enums import ReplacementReason

router = APIRouter(prefix="/replenishments", tags=["replenishments"])


@router.post("", response_model=ReplenishmentOut, status_code=201)
async def create_replenishment(
    body: CreateReplenishmentRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_CREATE, ENTITLEMENT_REPLENISHMENT)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_replenish(operator)
    obs = get_observability(request)
    started_at = body.started_at or datetime.now(UTC)
    key = idempotency_key or f"replenishment.create:{context.request_id}"
    raw = body.model_dump_json().encode("utf-8")
    obs.logger.info("replenishment.create.started", context=context)

    async def _handler(factory):
        result = await factory.start_replenishment().execute(
            StartReplenishmentCommand(
                operator=operator,
                machine_id=MachineId(UUID(body.machine_id)),
                started_at=started_at,
                location=GeoLocation(
                    latitude=body.location.latitude,
                    longitude=body.location.longitude,
                    accuracy=body.location.resolved_accuracy,
                ),
                idempotency_key=key,
            )
        )
        return replenishment_to_dict(result)

    payload = await run_mutating(
        session,
        context=context,
        operation="replenishment.create",
        idempotency_key=key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )
    obs.logger.info("replenishment.create.completed", context=context)
    return payload


@router.get(
    "/pending-product-resolutions",
    response_model=PendingProductResolutionsOut,
)
async def list_pending_product_resolutions(
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_RESOLVE_PRODUCT, ENTITLEMENT_REPLENISHMENT)
    ),
    machine_id: str | None = Query(default=None),
    replenishment_id: str | None = Query(default=None),
) -> dict:
    context, operator = access
    ensure_can_resolve_product(operator)
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    get_observability(request).logger.info(
        "replenishment.pending_product_resolutions",
        context=context,
    )

    async def _handler(factory):
        items = await factory.list_pending_product_resolutions().execute(
            ListPendingProductResolutionsQuery(
                tenant_id=tenant_id,
                machine_id=MachineId(UUID(machine_id)) if machine_id else None,
                replenishment_id=(
                    ReplenishmentId(UUID(replenishment_id)) if replenishment_id else None
                ),
            )
        )
        return {"items": [pending_resolution_to_dict(item) for item in items]}

    return await run_query(session, _handler)


@router.get("/{replenishment_id}", response_model=ReplenishmentOut)
async def get_replenishment(
    replenishment_id: str,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_READ, ENTITLEMENT_REPLENISHMENT)
    ),
) -> dict:
    context, _operator = access
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    get_observability(request).logger.info("replenishment.read", context=context)

    async def _handler(factory):
        result = await factory.get_replenishment().execute(
            GetReplenishmentQuery(
                replenishment_id=ReplenishmentId(UUID(replenishment_id)),
                tenant_id=tenant_id,
            )
        )
        return replenishment_to_dict(result)

    return await run_query(session, _handler)


@router.post("/{replenishment_id}/lines", response_model=ReplenishmentOut)
async def add_replenishment_line(
    replenishment_id: str,
    body: AddReplenishmentLineRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_ADD_LINE, ENTITLEMENT_REPLENISHMENT)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_replenish(operator)
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    reason = (
        ReplacementReason(body.replacement_reason)
        if body.replacement_reason is not None
        else None
    )
    raw = body.model_dump_json().encode("utf-8") + replenishment_id.encode()
    obs = get_observability(request)
    obs.logger.info("replenishment.add_line.started", context=context)

    async def _handler(factory):
        result = await factory.add_replenishment_line().execute(
            AddReplenishmentLineCommand(
                replenishment_id=ReplenishmentId(UUID(replenishment_id)),
                tenant_id=tenant_id,
                slot_id=SlotId(UUID(body.slot_id)),
                quantity=body.quantity,
                unit_price=body.unit_price,
                scanned_at=body.scanned_at or datetime.now(UTC),
                barcode=body.barcode,
                manual_description=body.manual_description,
                product_id=ProductId(UUID(body.product_id)) if body.product_id else None,
                replacement_reason=reason,
            )
        )
        return replenishment_to_dict(result)

    return await run_mutating(
        session,
        context=context,
        operation="replenishment.add_line",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )


@router.post(
    "/{replenishment_id}/lines/{line_id}/resolve-product",
    response_model=ReplenishmentOut,
)
async def resolve_replenishment_line_product(
    replenishment_id: str,
    line_id: str,
    body: ResolveReplenishmentLineProductRequest,
    request: Request,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_RESOLVE_PRODUCT, ENTITLEMENT_REPLENISHMENT)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_resolve_product(operator)
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    resolved_at = body.resolved_at or datetime.now(UTC)
    if body.resolved_at is not None:
        raw = f"{replenishment_id}:{line_id}:{body.product_id}:{body.resolved_at.isoformat()}"
    else:
        raw = f"{replenishment_id}:{line_id}:{body.product_id}"
    obs = get_observability(request)
    obs.logger.info("replenishment.resolve_product.started", context=context)

    async def _handler(factory):
        result = await factory.resolve_replenishment_line_product().execute(
            ResolveReplenishmentLineProductCommand(
                tenant_id=tenant_id,
                replenishment_id=ReplenishmentId(UUID(replenishment_id)),
                line_id=ReplenishmentLineId(UUID(line_id)),
                product_id=ProductId(UUID(body.product_id)),
                resolved_at=resolved_at,
                actor_operator_id=operator.id,
            )
        )
        return replenishment_to_dict(result)

    return await run_mutating(
        session,
        context=context,
        operation="replenishment.resolve_product",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw.encode("utf-8")),
        handler=_handler,
    )


@router.post("/{replenishment_id}/complete", response_model=ReplenishmentOut)
async def complete_replenishment(
    replenishment_id: str,
    request: Request,
    body: CompleteReplenishmentRequest | None = None,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_COMPLETE, ENTITLEMENT_REPLENISHMENT)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_replenish(operator)
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    payload = body or CompleteReplenishmentRequest()
    completed_at = payload.completed_at or datetime.now(UTC)
    # Hash must be stable across retries; do not include server-generated timestamps.
    if payload.completed_at is not None:
        raw = f"{replenishment_id}:{payload.completed_at.isoformat()}".encode()
    else:
        raw = f"{replenishment_id}".encode()
    obs = get_observability(request)
    obs.logger.info("replenishment.complete.started", context=context)

    async def _handler(factory):
        result = await factory.complete_replenishment().execute(
            CompleteReplenishmentCommand(
                replenishment_id=ReplenishmentId(UUID(replenishment_id)),
                tenant_id=tenant_id,
                completed_at=completed_at,
            )
        )
        return replenishment_to_dict(result)

    result = await run_mutating(
        session,
        context=context,
        operation="replenishment.complete",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )
    obs.logger.info("replenishment.complete.completed", context=context)
    return result


@router.post("/{replenishment_id}/cancel", response_model=ReplenishmentOut)
async def cancel_replenishment(
    replenishment_id: str,
    request: Request,
    body: CancelReplenishmentRequest | None = None,
    session: Session = Depends(get_db_session),
    access: tuple[RequestContext, Operator] = Depends(
        require_permission(REPLENISHMENT_CANCEL, ENTITLEMENT_REPLENISHMENT)
    ),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    context, operator = access
    ensure_can_replenish(operator)
    tenant_id = TenantId.from_raw(TenantContext.from_request(context).require_tenant_id())
    payload = body or CancelReplenishmentRequest()
    raw = f"{replenishment_id}:{payload.cancelled_at}".encode()
    get_observability(request).logger.info("replenishment.cancel.started", context=context)

    async def _handler(factory):
        result = await factory.cancel_replenishment().execute(
            CancelReplenishmentCommand(
                replenishment_id=ReplenishmentId(UUID(replenishment_id)),
                tenant_id=tenant_id,
                cancelled_at=payload.cancelled_at,
            )
        )
        return replenishment_to_dict(result)

    return await run_mutating(
        session,
        context=context,
        operation="replenishment.cancel",
        idempotency_key=idempotency_key,
        request_hash=request_hash_for(raw),
        handler=_handler,
    )
