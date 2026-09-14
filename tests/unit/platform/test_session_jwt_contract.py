"""Platform JwtService session round-trip (nexo-platform==1.11.0)."""

from __future__ import annotations

from importlib.metadata import version

from nexo_platform.identity import (
    AuthenticatedIdentity,
    AuthenticationResult,
    ExternalIdentity,
    JwtService,
    Principal,
    SessionToken,
)


def test_consumes_nexo_platform_1_11_0() -> None:
    assert version("nexo-platform") == "1.11.0"


def test_issue_and_decode_session_come_from_nexo_platform_package() -> None:
    assert JwtService.__module__.startswith("nexo_platform.")
    assert SessionToken.__module__.startswith("nexo_platform.")


def test_session_token_type_is_platform_session_token() -> None:
    identity = AuthenticatedIdentity(
        external_identity=ExternalIdentity(provider="google", subject="sub-1"),
        email="a@b.co",
    )
    result = AuthenticationResult(
        identity=identity,
        principal=Principal.from_authenticated_identity(identity),
    )
    jwt = JwtService(secret="platform-contract-secret", algorithm="HS256", issuer="nexo")
    session = jwt.issue_session(result, tenant_id="tenant-a", expires_in=120)
    assert isinstance(session, SessionToken)
    decoded = jwt.decode_session(session.access_token)
    assert decoded.tenant_id == "tenant-a"
    assert decoded.principal.provider == "google"
    assert decoded.principal.subject == "sub-1"
