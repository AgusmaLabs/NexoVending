# ADR-029: Vending HTTP API boundary

- Status: Accepted
- Date: 2026-09-11

## Context

V8 persisted replenishment and inventory via Platform `SqlAlchemyTransactionalUnitOfWork`. Clients still had no stable HTTP surface. V9 must expose existing use cases without embedding business rules in FastAPI.

## Decision

FastAPI is an **inbound adapter** only:

```text
HTTP → api routers/schemas → application use cases → domain → ports
                                      ↓
                         Platform (RequestContext, UoW,
                         IdempotencyService, Observability,
                         Authorization, Entitlement)
```

Rules:

1. Controllers do not contain domain rules and do not import SQLAlchemy repositories.
2. Composition (`UseCaseFactory`, UoW, idempotency) lives under `api/dependencies/`.
3. Tenant authority comes from Platform `RequestContext` / `X-Tenant-Id` + Principal — never from body `tenant_id`.
4. Permission / entitlement **codes** are owned by Vending; Platform provides the mechanism.
5. Mutating endpoints use Platform `IdempotencyService` when `Idempotency-Key` is present (same Session/UoW).
6. Observability uses Platform `Observability` contracts only.

Authentication in V9 accepted a trusted gateway principal token:

`Authorization: Bearer principal/<provider>/<subject>`

As of V12 (`nexo-platform==1.11.0`), business routes also accept Platform session JWTs from `JwtService.decode_session` (issued via `POST /api/v1/auth/session`). See [ADR-033](ADR-033-monolith-session-facade.md). Vending still does not implement OAuth/JWT crypto.

## Consequences

- OpenAPI documents HTTP DTOs, not domain entities.
- Architecture tests forbid FastAPI in domain/application and forbid router → SqlAlchemy repos.
- Platform idempotency table (`platform_idempotency_records`) must exist on shared PostgreSQL (Platform migrations / test DDL).

## Alternatives considered

1. Controllers calling repositories — rejected (breaks hexagonal boundary).
2. Product-local idempotency store — rejected (ADR-026 / Platform 1.8+).
3. Body `tenant_id` as isolation authority — rejected (ADR-005).
