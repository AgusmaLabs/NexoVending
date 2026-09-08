from datetime import UTC, datetime

from nexo_platform.identity.authentication import (
    AuthenticatedIdentity,
    AuthenticationResult,
    ExternalIdentity,
    Principal,
)
from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.value_objects import ValidityPeriod


def test_vending_accepts_platform_principal() -> None:
    principal = Principal(provider="google", subject="abc")
    assert principal.provider == "google"
    assert Principal.__module__.startswith("nexo_platform.")


def test_vending_accepts_platform_authenticated_identity() -> None:
    identity = AuthenticatedIdentity(
        external_identity=ExternalIdentity(provider="google", subject="abc"),
        email="a@b.com",
    )
    assert identity.external_identity.subject == "abc"
    assert AuthenticatedIdentity.__module__.startswith("nexo_platform.")
    assert ExternalIdentity.__module__.startswith("nexo_platform.")
    assert AuthenticationResult.__module__.startswith("nexo_platform.")


def test_operator_preserves_platform_principal() -> None:
    principal = Principal(provider="google", subject="xyz")
    operator = Operator(
        id=OperatorId.new(),
        tenant_id=TenantId("tenant-a"),
        principal=principal,
        role=OperatorRole.OPERATOR,
        status=OperatorStatus.PENDING,
        validity_period=ValidityPeriod(valid_from=datetime(2026, 1, 1, tzinfo=UTC)),
    )
    assert operator.principal is principal
    assert type(operator.principal).__module__.startswith("nexo_platform.")


def test_request_context_carries_platform_principal() -> None:
    principal = Principal(provider="google", subject="xyz")
    context = RequestContext.from_principal(tenant_id="tenant-a", principal=principal)
    assert context.principal == principal
    assert context.tenant_id == "tenant-a"
