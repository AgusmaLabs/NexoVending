# ADR-005: Tenant isolation boundary

- Status: Accepted
- Date: 2026-09-07

## Context

Even with a single initial business, Vending data must be isolatable by tenant. Platform already provides `RequestContext.tenant_id`.

## Decision

- Tenant is an **operational isolation boundary**.
- Application obtains `tenant_id` from authenticated `RequestContext` (Platform).
- Repositories / queries are scoped with that tenant.
- Clients must never supply the authoritative tenant id in payloads.

Domain entities in V2 do not embed `tenant_id` as a mandatory attribute; isolation is applied at the application/persistence boundary.

## Consequences

- Aligns with Platform tenancy without duplicating a second tenancy system.
- Domain stays free of Platform types (`RequestContext` is not imported in domain).
- Persistence adapters (future) must enforce tenant filters and constraints.

## Alternatives considered

1. Put `tenant_id` on every domain entity now — deferred; not required for in-memory foundation.
2. Trust client-sent tenant id — rejected.
