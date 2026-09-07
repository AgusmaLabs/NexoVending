# Architecture — NexoVending

## Dependency direction

```text
             nexo-platform
                   ▲
                   │
                   │ pip dependency (public API only)
                   │
             nexo-vending
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       Machine   Product  Inventory   ← planned (not implemented in V01)
```

Allowed:

```text
nexo_vending → nexo_platform
```

Forbidden:

```text
nexo_platform → nexo_vending
```

## What belongs where

### Platform (dependency)

- Tenant / RequestContext
- UnitOfWork
- DomainEvent / Outbox mechanism
- Identity, authorization, entitlement, billing (as published)
- Cross-cutting persistence primitives for Platform data

### Vending (this product)

- Vending domain (machines, products, slots, inventory, replenishment) — **planned**
- Vending application use cases
- Vending HTTP API
- Vending PostgreSQL schema + Alembic migrations
- Product-specific configuration (`APP_NAME`, `DATABASE_URL`, …)

## Hexagonal layout (V01)

```text
api/              FastAPI adapters (thin)
application/      use cases / orchestration
domain/           business model (empty in V01; boundary enforced)
infrastructure/   SQLAlchemy engine/session for Vending DB
```

Rules:

- `domain` must not import FastAPI, SQLAlchemy, or infrastructure.
- `api` depends on `application`, not on domain internals of Platform.
- Vending must not import `nexo_platform.persistence` or other internals.

## Runtime

```text
Request
  │
  ▼
Tenant RequestContext (Platform public contract)
  │
  ▼
Vending Application
  │
  ├─→ Vending PostgreSQL
  └─→ Platform contracts (events / UoW when needed)
```

## Implemented vs planned

| Capability | Status |
| --- | --- |
| Package bootstrap + Platform dependency | Implemented |
| Health / readiness | Implemented |
| Own Alembic + PostgreSQL | Implemented |
| Architecture / clean-install / Docker tests | Implemented |
| Machine / Product / Inventory / Restock | Planned |
| Agent Core integration | Future |

## Outbox and UnitOfWork

Vending does **not** duplicate Outbox or UnitOfWork. When business events are introduced, they will use Platform contracts (`DomainEvent`, Outbox) inside Vending transactions.
