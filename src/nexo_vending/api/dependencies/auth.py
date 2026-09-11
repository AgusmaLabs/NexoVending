"""Authentication → Principal → RequestContext (trusted gateway headers).

V9 does not implement OAuth/JWT. A trusted edge (or test client) supplies:

- Authorization: Bearer principal/<provider>/<subject>
- X-Tenant-Id: <tenant>

Optional: X-Request-Id
"""

from __future__ import annotations

from fastapi import Header, HTTPException, Request
from nexo_platform.identity.authentication import Principal
from nexo_platform.tenant import RequestContext


def _parse_bearer_principal(authorization: str | None) -> Principal:
    if authorization is None or not authorization.strip():
        raise HTTPException(status_code=401, detail="missing credentials")
    scheme, _, credentials = authorization.partition(" ")
    if scheme.lower() != "bearer" or not credentials.strip():
        raise HTTPException(status_code=401, detail="invalid authorization scheme")
    token = credentials.strip()
    if not token.startswith("principal/"):
        raise HTTPException(status_code=401, detail="unsupported credential format")
    parts = token.split("/", 2)
    if len(parts) != 3 or not parts[1] or not parts[2]:
        raise HTTPException(status_code=401, detail="invalid principal token")
    try:
        return Principal(provider=parts[1], subject=parts[2])
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


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

    if x_tenant_id is None or not str(x_tenant_id).strip():
        raise HTTPException(status_code=401, detail="X-Tenant-Id required")

    principal = _parse_bearer_principal(authorization)
    context = RequestContext.from_principal(
        principal=principal,
        tenant_id=str(x_tenant_id).strip(),
        request_id=x_request_id,
    )
    request.state.request_context = context
    return context
