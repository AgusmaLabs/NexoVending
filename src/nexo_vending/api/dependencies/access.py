"""Platform authorization / entitlement / operator resolution for HTTP."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request
from nexo_platform.authorization import AuthorizationService, Permission
from nexo_platform.entitlement import Entitlement, EntitlementService
from nexo_platform.observability import Observability
from nexo_platform.tenant import RequestContext
from sqlalchemy.orm import Session

from nexo_vending.api.dependencies.auth import get_request_context
from nexo_vending.api.dependencies.database import get_db_session
from nexo_vending.application.identity.resolve_operator import (
    ResolveOperator,
    ResolveOperatorQuery,
)
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.policies import (
    can_manage_catalog,
    can_manage_inventory,
    can_operator_replenish,
)
from nexo_vending.infrastructure.persistence import VendingPersistence


def get_authorization_service(request: Request) -> AuthorizationService:
    service = getattr(request.app.state, "authorization", None)
    if service is None:
        service = AuthorizationService()
        request.app.state.authorization = service
    return service


def get_entitlement_service(request: Request) -> EntitlementService:
    service = getattr(request.app.state, "entitlements", None)
    if service is None:
        service = EntitlementService()
        request.app.state.entitlements = service
    return service


def get_observability(request: Request) -> Observability:
    obs = getattr(request.app.state, "observability", None)
    if obs is None:
        obs = Observability.noop()
        request.app.state.observability = obs
    return obs


async def require_access(
    *,
    request: Request,
    context: RequestContext,
    permission: Permission,
    entitlement: Entitlement,
    session: Session,
) -> Operator:
    authz = get_authorization_service(request)
    ents = get_entitlement_service(request)
    obs = get_observability(request)

    if not await ents.is_enabled(context=context, entitlement=entitlement):
        obs.logger.info(
            "access.entitlement_denied",
            context=context,
            entitlement=entitlement.code,
        )
        raise HTTPException(status_code=403, detail="entitlement disabled")

    if not await authz.is_allowed(context=context, permission=permission):
        obs.logger.info(
            "access.permission_denied",
            context=context,
            permission=permission.code,
        )
        raise HTTPException(status_code=403, detail="permission denied")

    persistence = VendingPersistence.for_session(session)
    operator = await ResolveOperator(persistence.operators).execute(
        ResolveOperatorQuery(context=context)
    )
    return operator


def require_permission(permission: Permission, entitlement: Entitlement):
    async def _dependency(
        request: Request,
        context: RequestContext = Depends(get_request_context),
        session: Session = Depends(get_db_session),
    ) -> tuple[RequestContext, Operator]:
        operator = await require_access(
            request=request,
            context=context,
            permission=permission,
            entitlement=entitlement,
            session=session,
        )
        return context, operator

    return _dependency


def ensure_can_replenish(operator: Operator, *, at: datetime | None = None) -> None:
    moment = at or datetime.now(UTC)
    if not can_operator_replenish(operator, moment):
        raise PermissionError("operator cannot replenish")


def ensure_can_manage_inventory(operator: Operator) -> None:
    if not can_manage_inventory(operator):
        raise PermissionError("operator cannot manage inventory")


def ensure_can_resolve_product(operator: Operator) -> None:
    if not can_manage_catalog(operator):
        raise PermissionError("operator cannot resolve replenishment products")
