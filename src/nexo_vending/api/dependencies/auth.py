"""Authentication → Principal → RequestContext (harness + Platform session JWT).

Credentials:

- Authorization: Bearer principal/<provider>/<subject>  (+ required X-Tenant-Id)
- Authorization: Bearer <session JWT>  (tenant from decode_session; X-Tenant-Id optional match)

Vending does not implement OAuth/JWT crypto; JwtService comes from Platform.
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request
from nexo_platform.identity import InvalidSessionTokenError, JwtService, Principal
from nexo_platform.tenant import RequestContext


def _parse_bearer_token(authorization: str | None) -> str:
    if authorization is None or not authorization.strip():
        raise HTTPException(status_code=401, detail="missing credentials")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise HTTPException(status_code=401, detail="invalid authorization scheme")
    return credentials.strip()


def _parse_bearer_principal(token: str) -> Principal:
    if not token.startswith("principal/"):
        raise HTTPException(status_code=401, detail="unsupported credential format")
    parts = token.split("/", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise HTTPException(status_code=401, detail="invalid principal token")
    try:
        return Principal(provider=parts[1], subject=parts[2])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _jwt_service(request: Request) -> JwtService:
    service = getattr(request.app.state, "jwt_service", None)
    if service is None:
        raise HTTPException(status_code=500, detail="jwt service not configured")
    return service


async def get_request_context(
    request: Request,
    authorization: str | None = Header(default=None),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> RequestContext:
    override = getattr(request.app.state, "auth_context_override", None)
    if callable(override):
        context = override(request)
        request.state.request_context = context
        return context

    token = _parse_bearer_token(authorization)

    if token.startswith("principal/"):
        if x_tenant_id is None or not str(x_tenant_id).strip():
            raise HTTPException(status_code=401, detail="X-Tenant-Id required")
        principal = _parse_bearer_principal(token)
        context = RequestContext.from_principal(
            principal=principal,
            tenant_id=str(x_tenant_id).strip(),
            request_id=x_request_id,
        )
        request.state.request_context = context
        return context

    try:
        session = _jwt_service(request).decode_session(token)
    except InvalidSessionTokenError as exc:
        raise HTTPException(status_code=401, detail="invalid session token") from exc
    except Exception as exc:  # noqa: BLE001 — map any Platform JWT failure to 401
        raise HTTPException(status_code=401, detail="invalid session token") from exc

    if x_tenant_id is not None and str(x_tenant_id).strip():
        header_tenant = str(x_tenant_id).strip()
        if header_tenant != session.tenant_id:
            raise HTTPException(status_code=401, detail="X-Tenant-Id does not match session")

    context = RequestContext.from_principal(
        principal=session.principal,
        tenant_id=session.tenant_id,
        request_id=x_request_id,
    )
    request.state.request_context = context
    return context
