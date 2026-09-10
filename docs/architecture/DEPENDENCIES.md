# Dependency Rules — NexoVending

## External

```text
nexo_vending ──► nexo_platform   (public API only; Application/API layers)
nexo_platform ─✕─► nexo_vending
```

## Internal layers

```text
api            ──► application
application    ──► domain (ports / entities)
infrastructure ──► domain ports
domain         ─✕─► api | infrastructure | fastapi | sqlalchemy | nexo_platform
```

## Domain modules

Allowed conceptual dependencies:

```text
identity      ──► common + nexo_platform.identity.authentication (Principal only)
replenishment ──► machines, common
inventory     ──► common
machines      ──► common
products      ──► common
```

Forbidden:

```text
products ─✕─► replenishment
domain (non-identity) ─✕─► nexo_platform
domain ─✕─► Google / OAuth / JWT SDKs
```

## Tenant isolation

```text
RequestContext  (Platform)
        │
        ▼
 TenantContext.from_request(...).require_tenant_id()
        │
        ▼
   Application (tenant_context helpers)
        │
        ▼
 Domain TenantId / tenant-scoped aggregates
        │
        ▼
 Repository queries (scoped by authenticated tenant)
```

Never:

```text
WHERE tenant_id = <client payload>
```

Persistence (V8) must also enforce tenant via columns and constraints. See [ADR-005](../adr/ADR-005-tenant-isolation.md).

## Platform persistence contracts

- Allowed public packages: `nexo_platform.transaction`, `nexo_platform.persistence` (`Database`, `SessionFactory` only), `nexo_platform.tenant`, `nexo_platform.context`, `events`, `outbox`, identity/authz/entitlement as published.
- Forbidden: `nexo_platform.persistence.database` / `persistence.sqlalchemy` internals; billing domain trees; other infrastructure modules.
- Vending binds `DATABASE_URL` through public `Database.from_url`; owns Alembic for domain tables.
- No product-local `VendingUnitOfWork`; use `SqlAlchemyTransactionalUnitOfWork`.

Details: [PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md), [ADR-026](../adr/ADR-026-platform-persistence-integration.md).

## Concurrency (inventory)

Domain defines available quantity and rejects negative stock.

Lost-update prevention under concurrent consumptions is a **persistence** concern (locking / optimistic version) and must not be “solved” only with in-process Python assumptions.
