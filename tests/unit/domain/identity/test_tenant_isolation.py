import asyncio
from datetime import UTC, datetime

import pytest
from nexo_platform.identity.authentication import Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.application.identity.resolve_operator import (
    ResolveOperator,
    ResolveOperatorQuery,
)
from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.errors import OperatorNotFoundError
from nexo_vending.domain.identity.value_objects import ValidityPeriod
from tests.support.fakes import InMemoryOperatorRepository


def _make_operator(tenant: str, subject: str, status: OperatorStatus) -> Operator:
    return Operator(
        id=OperatorId.new(),
        tenant_id=TenantId(tenant),
        principal=Principal(provider="google", subject=subject),
        role=OperatorRole.OPERATOR,
        status=status,
        validity_period=ValidityPeriod(valid_from=datetime(2026, 1, 1, tzinfo=UTC)),
    )


def test_operator_lookup_is_tenant_scoped() -> None:
    asyncio.run(_test_operator_lookup_is_tenant_scoped())


async def _test_operator_lookup_is_tenant_scoped() -> None:
    repo = InMemoryOperatorRepository()
    principal = Principal(provider="google", subject="123")
    op_a = _make_operator("tenant-a", "123", OperatorStatus.ACTIVE)
    op_b = _make_operator("tenant-b", "123", OperatorStatus.SUSPENDED)
    await repo.save(op_a)
    await repo.save(op_b)

    found = await repo.find_by_principal(TenantId("tenant-b"), principal)
    assert found is not None
    assert found.id == op_b.id
    assert found.status == OperatorStatus.SUSPENDED


def test_same_principal_can_exist_in_different_tenants() -> None:
    asyncio.run(_test_same_principal_can_exist_in_different_tenants())


async def _test_same_principal_can_exist_in_different_tenants() -> None:
    repo = InMemoryOperatorRepository()
    await repo.save(_make_operator("tenant-a", "123", OperatorStatus.ACTIVE))
    await repo.save(_make_operator("tenant-b", "123", OperatorStatus.SUSPENDED))
    a = await repo.find_by_principal(
        TenantId("tenant-a"), Principal(provider="google", subject="123")
    )
    b = await repo.find_by_principal(
        TenantId("tenant-b"), Principal(provider="google", subject="123")
    )
    assert a is not None and b is not None
    assert a.id != b.id


def test_operator_from_other_tenant_is_not_resolved() -> None:
    asyncio.run(_test_operator_from_other_tenant_is_not_resolved())


async def _test_operator_from_other_tenant_is_not_resolved() -> None:
    repo = InMemoryOperatorRepository()
    await repo.save(_make_operator("tenant-a", "123", OperatorStatus.ACTIVE))
    found = await repo.find_by_principal(
        TenantId("tenant-b"), Principal(provider="google", subject="123")
    )
    assert found is None


def test_cross_tenant_operator_access_is_rejected() -> None:
    asyncio.run(_test_cross_tenant_operator_access_is_rejected())


async def _test_cross_tenant_operator_access_is_rejected() -> None:
    repo = InMemoryOperatorRepository()
    await repo.save(_make_operator("tenant-a", "123", OperatorStatus.ACTIVE))
    context = RequestContext.from_principal(
        tenant_id="tenant-b",
        principal=Principal(provider="google", subject="123"),
    )
    with pytest.raises(OperatorNotFoundError):
        await ResolveOperator(repo).execute(ResolveOperatorQuery(context=context))
