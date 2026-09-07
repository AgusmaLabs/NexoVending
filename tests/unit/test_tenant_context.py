from uuid import uuid4

from nexo_platform import DomainEvent, Tenant, UnitOfWork
from nexo_platform.tenant import RequestContext

from nexo_vending.application.tenant_context import (
    bind_request_context,
    get_request_context,
    get_tenant_id,
)


def test_can_import_platform_public_api() -> None:
    assert Tenant is not None
    assert UnitOfWork is not None
    event = DomainEvent(event_type="vending.bootstrap", tenant_id="tenant-a")
    assert event.event_type == "vending.bootstrap"
    assert event.tenant_id == "tenant-a"


def test_request_context_does_not_leak_across_bindings() -> None:
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())
    ctx_a = RequestContext(tenant_id=tenant_a, actor_id="actor-a")
    ctx_b = RequestContext(tenant_id=tenant_b, actor_id="actor-b")

    assert get_request_context() is None

    with bind_request_context(ctx_a):
        assert get_tenant_id() == tenant_a
        with bind_request_context(ctx_b):
            assert get_tenant_id() == tenant_b
        assert get_tenant_id() == tenant_a

    assert get_request_context() is None
