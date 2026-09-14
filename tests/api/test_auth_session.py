"""API tests for session facade and dual-credential auth."""

from __future__ import annotations

from dataclasses import dataclass, field

from nexo_platform.identity import (
    AuthenticatedIdentity,
    AuthenticationCredentials,
    AuthenticationResult,
    ExternalIdentity,
    InvalidCredentialsError,
    JwtService,
    Principal,
)

from tests.api.conftest import admin_headers, api, replenisher_headers


@dataclass
class FakeAuthProvider:
    mapping: dict[str, AuthenticationResult] = field(default_factory=dict)
    fail: bool = False

    async def authenticate(self, credentials: AuthenticationCredentials) -> AuthenticationResult:
        if self.fail or credentials.kind != "id_token":
            raise InvalidCredentialsError("invalid id_token")
        token = credentials.require("id_token")
        if token not in self.mapping:
            raise InvalidCredentialsError("unknown id_token")
        return self.mapping[token]


def _auth_result(subject: str) -> AuthenticationResult:
    identity = AuthenticatedIdentity(
        external_identity=ExternalIdentity(provider="google", subject=subject),
        email=f"{subject}@example.com",
    )
    return AuthenticationResult(
        identity=identity,
        principal=Principal.from_authenticated_identity(identity),
    )


def _wire_session_auth(world: dict, *, subjects: dict[str, str] | None = None) -> JwtService:
    """Attach JwtService + FakeAuthProvider to the test app."""
    jwt = JwtService(secret="api-session-secret", algorithm="HS256", issuer="nexo-test")
    mapping = {
        f"id-token-{subject}": _auth_result(subject)
        for subject in (subjects or {"replenisher": world["replenisher_subject"]}).values()
    }
    # Map by explicit tokens
    if subjects is None:
        mapping = {
            "id-token-replenisher": _auth_result(world["replenisher_subject"]),
            "id-token-admin": _auth_result(world["admin_subject"]),
            "id-token-unknown": _auth_result("nobody"),
        }
    provider = FakeAuthProvider(mapping=mapping)
    world["app"].state.jwt_service = jwt
    world["app"].state.authentication_provider = provider
    world["jwt"] = jwt
    return jwt


def test_post_auth_session_returns_bearer_token(api_world) -> None:
    _wire_session_auth(api_world)
    client = api_world["client"]
    response = client.post(
        api("/auth/session"),
        json={"id_token": "id-token-replenisher", "tenant_id": "tenant-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "Bearer"
    assert body["expires_in"] > 0
    assert body["access_token"]
    session = api_world["jwt"].decode_session(body["access_token"])
    assert session.tenant_id == "tenant-a"
    assert session.principal.subject == api_world["replenisher_subject"]


def test_post_auth_session_invalid_id_token_401(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].post(
        api("/auth/session"),
        json={"id_token": "nope", "tenant_id": "tenant-a"},
    )
    assert response.status_code == 401


def test_post_auth_session_unknown_operator_403(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].post(
        api("/auth/session"),
        json={"id_token": "id-token-unknown", "tenant_id": "tenant-a"},
    )
    assert response.status_code == 403


def test_post_auth_session_validation_error_422(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].post(api("/auth/session"), json={"tenant_id": "tenant-a"})
    assert response.status_code == 422


def test_get_operators_me_with_session_jwt_200(api_world) -> None:
    jwt = _wire_session_auth(api_world)
    client = api_world["client"]
    issued = client.post(
        api("/auth/session"),
        json={"id_token": "id-token-replenisher", "tenant_id": "tenant-a"},
    ).json()
    response = client.get(
        api("/operators/me"),
        headers={"Authorization": f"Bearer {issued['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["operator_id"] == api_world["replenisher_id"]
    assert body["tenant_id"] == "tenant-a"
    assert body["role"] == "operator"
    assert body["subject"] == api_world["replenisher_subject"]
    # ensure JWT decode works for harness-free path
    assert jwt.decode_session(issued["access_token"]).tenant_id == "tenant-a"


def test_business_route_accepts_session_jwt_without_inventing_principal_token(api_world) -> None:
    _wire_session_auth(api_world)
    client = api_world["client"]
    issued = client.post(
        api("/auth/session"),
        json={"id_token": "id-token-replenisher", "tenant_id": "tenant-a"},
    ).json()["access_token"]
    response = client.post(
        api("/replenishments"),
        headers={
            "Authorization": f"Bearer {issued}",
            "Idempotency-Key": "session-jwt-create-1",
        },
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 201


def test_business_route_still_accepts_harness_principal_token(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].post(
        api("/replenishments"),
        headers=replenisher_headers(api_world, key="harness-still-ok"),
        json={
            "machine_id": api_world["machine_id"],
            "location": {"latitude": -33.4, "longitude": -70.6, "accuracy": 5.0},
        },
    )
    assert response.status_code == 201


def test_session_jwt_rejects_mismatched_x_tenant_id(api_world) -> None:
    _wire_session_auth(api_world)
    client = api_world["client"]
    token = client.post(
        api("/auth/session"),
        json={"id_token": "id-token-replenisher", "tenant_id": "tenant-a"},
    ).json()["access_token"]
    response = client.get(
        api("/operators/me"),
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-Id": "tenant-b",
        },
    )
    assert response.status_code == 401


def test_session_jwt_allows_omitted_x_tenant_id(api_world) -> None:
    _wire_session_auth(api_world)
    client = api_world["client"]
    token = client.post(
        api("/auth/session"),
        json={"id_token": "id-token-replenisher", "tenant_id": "tenant-a"},
    ).json()["access_token"]
    response = client.get(
        api("/operators/me"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_expired_or_invalid_jwt_returns_401(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].get(
        api("/operators/me"),
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401


def test_get_operators_me_with_harness(api_world) -> None:
    _wire_session_auth(api_world)
    response = api_world["client"].get(
        api("/operators/me"),
        headers=admin_headers(api_world),
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"
