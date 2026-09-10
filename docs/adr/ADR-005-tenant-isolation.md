# ADR-005: Tenant isolation boundary

- Status: Accepted
- Date: 2026-09-07
- Updated: 2026-09-09

## Context

Even with a single initial business, Vending data must be isolatable by tenant. Platform already provides `RequestContext.tenant_id`.

Domain aggregates for operators, products, and machines carry `tenant_id` as part of their identity/ownership. Inventory/replenishment flows receive tenant from Application commands or parent aggregates.

## Decision

- Tenant is an **operational isolation boundary**.
- Application obtains authoritative `tenant_id` from authenticated `RequestContext` (Platform) via `application/tenant_context`.
- Domain uses Vending `TenantId` value objects; Domain does **not** import `RequestContext`.
- Where business ownership is tenant-scoped, entities embed `tenant_id` (operators, products, machines, and related aggregates as modeled).
- Repositories / queries are scoped with the authenticated tenant.
- Clients must never supply the authoritative tenant id in payloads.
- Persistence adapters (V8, after Platform generic UoW) must enforce tenant filters and tenant-aware UNIQUE/FK/CHECK constraints; isolation must be tested against PostgreSQL.

## Consequences

- Aligns with Platform tenancy without duplicating a second tenancy system.
- Domain stays free of Platform types (`RequestContext` is Application-only).
- ADR-026 gates SQL enforcement on the Platform transactional contract + V8.

## Alternatives considered

1. Keep tenant only at the application/persistence boundary with no `tenant_id` on entities — rejected for current model; ownership and uniqueness rules require tenant on tenant-scoped aggregates.
2. Trust client-sent tenant id — rejected.
