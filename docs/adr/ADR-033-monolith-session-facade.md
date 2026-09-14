# ADR-033: Monolith session facade

- Status: Accepted
- Date: 2026-09-14

## Context

Flutter needs a single base URL (`nexovending.com`) in the monolith stage. Platform `1.11.0` publishes `JwtService.issue_session` / `decode_session` / `SessionToken` with tenant claims. Vending must not become an IdP or reimplement JWT/OAuth.

## Decision

1. NexoVending is the sole HTTP entry for the mobile app in this stage.
2. `POST /api/v1/auth/session` is a thin adapter: Platform `AuthenticationProvider.authenticate` → accept `tenant_id` only if a Vending `Operator` exists → `JwtService.issue_session`.
3. Business routes accept `Authorization: Bearer <session JWT>`; `decode_session.tenant_id` is authority. Optional `X-Tenant-Id` must match when present.
4. Harness `Bearer principal/<provider>/<subject>` + required `X-Tenant-Id` remains for tests/CI.
5. `GoogleOAuthProvider` (Platform INTERNAL) may be imported only from `api/dependencies/auth_providers.py`.
6. JWT claims never authorize replenishment; `ResolveOperator` + Operator policies remain the authority.
7. `GET /api/v1/operators/me` bootstraps the authenticated Operator for Flutter.

## Consequences

- Dependency pin moves to `nexo-platform==1.11.0`.
- ADR-029 dual-credential auth is Implemented.
- A future extracted gateway can replace the composition root without changing domain use cases.

## Alternatives considered

1. Separate Platform HTTP gateway now — rejected (two hosts for Flutter).
2. OAuth/JWT implemented inside Vending — rejected (ADR-006).
3. Production-only `principal/...` tokens invented by the app — rejected.
