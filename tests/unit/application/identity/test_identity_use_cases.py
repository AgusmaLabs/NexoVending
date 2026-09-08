import asyncio

import pytest
from nexo_platform.identity.authentication import AuthenticatedIdentity, ExternalIdentity, Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.application.identity.activate_operator import (
    ActivateOperator,
    ActivateOperatorCommand,
)
from nexo_vending.application.identity.assign_operator_role import (
    AssignOperatorRole,
    AssignOperatorRoleCommand,
)
from nexo_vending.application.identity.disable_operator import (
    DisableOperator,
    DisableOperatorCommand,
)
from nexo_vending.application.identity.provision_operator import (
    ProvisionOperator,
    ProvisionOperatorCommand,
)
from nexo_vending.application.identity.resolve_operator import (
    ResolveOperator,
    ResolveOperatorQuery,
)
from nexo_vending.application.identity.suspend_operator import (
    SuspendOperator,
    SuspendOperatorCommand,
)
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.errors import IdentityError
from tests.support.fakes import InMemoryOperatorRepository


def _identity(subject: str = "123") -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        external_identity=ExternalIdentity(provider="google", subject=subject),
        email="user@example.com",
        display_name="Operator One",
    )


def _context(tenant: str = "tenant-a", subject: str = "123") -> RequestContext:
    return RequestContext.from_principal(
        tenant_id=tenant,
        principal=Principal(provider="google", subject=subject),
    )


def test_provision_operator() -> None:
    asyncio.run(_test_provision_operator())


async def _test_provision_operator() -> None:
    repo = InMemoryOperatorRepository()
    operator = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    assert operator.status == OperatorStatus.PENDING
    assert operator.principal.subject == "123"
    assert operator.tenant_id.value == "tenant-a"


def test_existing_operator_is_resolved() -> None:
    asyncio.run(_test_existing_operator_is_resolved())


async def _test_existing_operator_is_resolved() -> None:
    repo = InMemoryOperatorRepository()
    first = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    second = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    assert first.id == second.id


def test_activate_operator() -> None:
    asyncio.run(_test_activate_operator())


async def _test_activate_operator() -> None:
    repo = InMemoryOperatorRepository()
    operator = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    activated = await ActivateOperator(repo).execute(
        ActivateOperatorCommand(operator_id=operator.id)
    )
    assert activated.status == OperatorStatus.ACTIVE


def test_suspend_operator() -> None:
    asyncio.run(_test_suspend_operator())


async def _test_suspend_operator() -> None:
    repo = InMemoryOperatorRepository()
    operator = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    await ActivateOperator(repo).execute(ActivateOperatorCommand(operator_id=operator.id))
    suspended = await SuspendOperator(repo).execute(
        SuspendOperatorCommand(operator_id=operator.id)
    )
    assert suspended.status == OperatorStatus.SUSPENDED


def test_disable_operator() -> None:
    asyncio.run(_test_disable_operator())


async def _test_disable_operator() -> None:
    repo = InMemoryOperatorRepository()
    operator = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    await ActivateOperator(repo).execute(ActivateOperatorCommand(operator_id=operator.id))
    disabled = await DisableOperator(repo).execute(
        DisableOperatorCommand(operator_id=operator.id)
    )
    assert disabled.status == OperatorStatus.DISABLED


def test_assign_operator_role() -> None:
    asyncio.run(_test_assign_operator_role())


async def _test_assign_operator_role() -> None:
    repo = InMemoryOperatorRepository()
    operator = await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    updated = await AssignOperatorRole(repo).execute(
        AssignOperatorRoleCommand(operator_id=operator.id, role=OperatorRole.ADMIN)
    )
    assert updated.role == OperatorRole.ADMIN


def test_resolve_operator_uses_context_tenant() -> None:
    asyncio.run(_test_resolve_operator_uses_context_tenant())


async def _test_resolve_operator_uses_context_tenant() -> None:
    repo = InMemoryOperatorRepository()
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context("tenant-a"), identity=_identity())
    )
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context("tenant-b"), identity=_identity())
    )
    resolved = await ResolveOperator(repo).execute(
        ResolveOperatorQuery(context=_context("tenant-b"))
    )
    assert resolved.tenant_id.value == "tenant-b"


def test_resolve_operator_uses_context_principal() -> None:
    asyncio.run(_test_resolve_operator_uses_context_principal())


async def _test_resolve_operator_uses_context_principal() -> None:
    repo = InMemoryOperatorRepository()
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(subject="aaa"), identity=_identity("aaa"))
    )
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(subject="bbb"), identity=_identity("bbb"))
    )
    resolved = await ResolveOperator(repo).execute(
        ResolveOperatorQuery(context=_context(subject="bbb"))
    )
    assert resolved.principal.subject == "bbb"


def test_client_cannot_override_tenant() -> None:
    asyncio.run(_test_client_cannot_override_tenant())


async def _test_client_cannot_override_tenant() -> None:
    repo = InMemoryOperatorRepository()
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context("tenant-a"), identity=_identity())
    )
    with pytest.raises(IdentityError, match="cannot override tenant"):
        await ResolveOperator(repo).execute(
            ResolveOperatorQuery(
                context=_context("tenant-a"),
                claimed_tenant_id="tenant-b",
            )
        )


def test_client_cannot_override_actor() -> None:
    asyncio.run(_test_client_cannot_override_actor())


async def _test_client_cannot_override_actor() -> None:
    repo = InMemoryOperatorRepository()
    await ProvisionOperator(repo).execute(
        ProvisionOperatorCommand(context=_context(), identity=_identity())
    )
    with pytest.raises(IdentityError, match="cannot override actor"):
        await ResolveOperator(repo).execute(
            ResolveOperatorQuery(
                context=_context(),
                claimed_operator_id="some-other-id",
            )
        )
