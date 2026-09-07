"""Tenant/request context propagation using Platform's public RequestContext."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from uuid import UUID

from nexo_platform.tenant import RequestContext

_current_context: ContextVar[RequestContext | None] = ContextVar(
    "nexo_vending_request_context",
    default=None,
)


def get_request_context() -> RequestContext | None:
    return _current_context.get()


def require_request_context() -> RequestContext:
    context = get_request_context()
    if context is None:
        raise RuntimeError("RequestContext is not bound for the current request")
    return context


def get_tenant_id() -> str | UUID:
    return require_request_context().tenant_id


@contextmanager
def bind_request_context(context: RequestContext) -> Iterator[RequestContext]:
    """Bind a Platform RequestContext for the duration of a Vending request."""
    token: Token[RequestContext | None] = _current_context.set(context)
    try:
        yield context
    finally:
        _current_context.reset(token)
