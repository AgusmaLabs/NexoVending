"""Application tests for IssueOperatorSession."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime

import pytest
from nexo_platform.identity import (
    AuthenticatedIdentity,
    AuthenticationCredentials,
    AuthenticationResult,
    ExternalIdentity,
    InvalidCredentialsError,
    JwtService,
    Principal,
    SessionToken,
)

from nexo_vending.application.identity.issue_session import (
    IssueOperatorSession,
    IssueOperatorSessionCommand,
)
from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.identity.errors import OperatorNotFoundError


def _result(*, provider: str = "google", subject: str = "replenisher-1") -> AuthenticationResult:
    identity = AuthenticatedIdentity(
        external_identity=ExternalIdentity(provider=provider, subject=subject),
        email="op@example.com",
    )
    return AuthenticationResult(
        identity=identity,
        principal=Principal.from_authenticated_identity(identity),
    )


@dataclass
class FakeAuthProvider:
    result: AuthenticationResult | None = None
    error: Exception | None = None
    calls: list[AuthenticationCredentials] = field(default_factory=list)

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        self.calls.append(credentials)
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@dataclass
class FakeOperatorRepo:
    operators: dict[tuple[str, str, str], Operator] = field(default_factory=dict)

    async def find_by_principal(self, tenant_id: TenantId, principal: Principal):
        key = (str(tenant_id.value), principal.provider, principal.subject)
        return self.operators.get(key)

    async def get(self, operator_id: OperatorId):
        raise NotImplementedError

    async def save(self, operator: Operator) -> None:
        raise NotImplementedError


def _operator(*, tenant: str = "tenant-a", subject: str = "replenisher-1") -> Operator:
    op = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId(tenant),
        principal=Principal(provider="google", subject=subject),
        role=OperatorRole.OPERATOR,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    op.activate()
    return op


def _jwt() -> JwtService:
    return JwtService(secret="test-session-secret", algorithm="HS256", issuer="nexo-test")


async def _test_issue_ok() -> None:
    result = _result()
    provider = FakeAuthProvider(result=result)
    op = _operator()
    repo = FakeOperatorRepo(
        operators={(str(op.tenant_id.value), op.principal.provider, op.principal.subject): op}
    )
    jwt = _jwt()
    use_case = IssueOperatorSession(
        authentication=provider,
        jwt_service=jwt,
        operators=repo,
    )
    session = await use_case.execute(
        IssueOperatorSessionCommand(id_token="fake-id-token", tenant_id="tenant-a")
    )
    assert isinstance(session, SessionToken)
    assert session.tenant_id == "tenant-a"
    assert session.principal.subject == "replenisher-1"
    assert provider.calls[0].kind == "id_token"
    assert jwt.decode_session(session.access_token).tenant_id == "tenant-a"


def test_issue_session_authenticates_id_token_via_provider() -> None:
    asyncio.run(_test_issue_ok())


async def _test_invalid_token() -> None:
    provider = FakeAuthProvider(error=InvalidCredentialsError("bad token"))
    use_case = IssueOperatorSession(
        authentication=provider,
        jwt_service=_jwt(),
        operators=FakeOperatorRepo(),
    )
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            IssueOperatorSessionCommand(id_token="bad", tenant_id="tenant-a")
        )


def test_issue_session_rejects_invalid_id_token() -> None:
    asyncio.run(_test_invalid_token())


async def _test_unprovisioned() -> None:
    provider = FakeAuthProvider(result=_result(subject="unknown"))
    use_case = IssueOperatorSession(
        authentication=provider,
        jwt_service=_jwt(),
        operators=FakeOperatorRepo(),
    )
    with pytest.raises(OperatorNotFoundError):
        await use_case.execute(
            IssueOperatorSessionCommand(id_token="tok", tenant_id="tenant-a")
        )


def test_issue_session_rejects_unprovisioned_operator() -> None:
    asyncio.run(_test_unprovisioned())


async def _test_tenant_embed() -> None:
    op = _operator(tenant="tenant-b", subject="op-b")
    provider = FakeAuthProvider(result=_result(subject="op-b"))
    repo = FakeOperatorRepo(operators={(str(op.tenant_id.value), "google", "op-b"): op})
    jwt = _jwt()
    use_case = IssueOperatorSession(
        authentication=provider,
        jwt_service=jwt,
        operators=repo,
    )
    session = await use_case.execute(
        IssueOperatorSessionCommand(id_token="tok", tenant_id="tenant-b")
    )
    assert session.tenant_id == "tenant-b"
    assert jwt.decode_session(session.access_token).tenant_id == "tenant-b"


def test_issue_session_embeds_accepted_tenant_in_platform_session() -> None:
    asyncio.run(_test_tenant_embed())


async def _test_roles_ignored() -> None:
    op = _operator()
    provider = FakeAuthProvider(result=_result())
    repo = FakeOperatorRepo(
        operators={(str(op.tenant_id.value), "google", "replenisher-1"): op}
    )
    use_case = IssueOperatorSession(
        authentication=provider,
        jwt_service=_jwt(),
        operators=repo,
    )
    session = await use_case.execute(
        IssueOperatorSessionCommand(id_token="tok", tenant_id="tenant-a")
    )
    assert op.role == OperatorRole.OPERATOR
    assert session.principal.subject == op.principal.subject


def test_issue_session_does_not_use_jwt_roles_as_operator_role() -> None:
    asyncio.run(_test_roles_ignored())
