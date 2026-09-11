# Architecture — NexoVending

## Dependency direction

```text
             nexo-platform
                   ▲
                   │
                   │ pip dependency (public API only; Application/API)
                   │
             nexo-vending
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       Machine   Product  Inventory / Replenishment
```

Allowed: `nexo_vending → nexo_platform`  
Forbidden: `nexo_platform → nexo_vending`  
Forbidden in **domain**: any `nexo_platform` import (except identity `Principal` binding).

## What belongs where

### Platform (dependency) — `nexo-platform==1.10.0`

- Tenant / `RequestContext` / `TenantContext`
- Public persistence: `Database`, `SessionFactory`
- Generic transactional UoW: `TransactionalUnitOfWork`, `SqlAlchemyTransactionalUnitOfWork`
- Transaction primitives (`RetryPolicy`, `TransactionConflict`, `NestedTransactionError`)
- Idempotency / Feature flags / Observability contracts (**Idempotency + Observability wired in V9**)
- DomainEvent / Outbox record shapes
- Identity, authorization, entitlement, billing (as published)

### Vending (this product)

- Domain: products, machines/slots, inventory ledger, replenishment aggregate (**implemented**)
- Application use cases for replenishment / inventory / sales (**implemented**)
- HTTP health API (**implemented**)
- Business HTTP API for replenishment & inventory (**implemented** — V9)
- Composition helpers around Platform `Database` (**implemented**)
- Platform integration decisions (**implemented** — see [PLATFORM_INTEGRATION.md](docs/architecture/PLATFORM_INTEGRATION.md))
- Vending PostgreSQL schema for domain tables (**implemented** — V8)
- Sales / Admin / Flutter APIs (**planned**)

## Hexagonal layout

```text
api/                 FastAPI adapters (thin)
application/         use cases (identity, products, machines, replenishment, inventory, sales)
domain/
  common/            IDs, VOs, errors
  identity/          Operator contract
  products/          Product + ports
  machines/          Machine aggregate + physical slots
  inventory/         InventoryMovement + InventoryLedger
  replenishment/     Replenishment aggregate
  sales/             Snack / coffee consumption
infrastructure/      Database helpers + SQLAlchemy persistence adapters (V8)
```

See also:

- [docs/architecture/PLATFORM_INTEGRATION.md](docs/architecture/PLATFORM_INTEGRATION.md)
- [docs/architecture/PRODUCT_CATALOG.md](docs/architecture/PRODUCT_CATALOG.md)
- [docs/architecture/MACHINE_MANAGEMENT.md](docs/architecture/MACHINE_MANAGEMENT.md)
- [docs/architecture/INVENTORY_AND_REPLENISHMENT.md](docs/architecture/INVENTORY_AND_REPLENISHMENT.md)
- [docs/domain/PRODUCT_CATALOG_RULES.md](docs/domain/PRODUCT_CATALOG_RULES.md)
- [docs/domain/MACHINE_AND_SLOT_RULES.md](docs/domain/MACHINE_AND_SLOT_RULES.md)

## Runtime

```text
Request
  │
  ▼
RequestContext / TenantContext (Platform)     ← Application only
  │
  ▼
Vending Application use cases
  │
  ▼
Domain aggregates / ledger
```

V8 transactional path:

```text
RequestContext
  → Application use case
  → Database.session_factory() → Session
  → SqlAlchemyTransactionalUnitOfWork(session)
  → Vending repository adapters (shared Session)
  → Domain
```

## Implemented vs planned

| Capability | Status |
| --- | --- |
| Package bootstrap + Platform dependency | Implemented (`nexo-platform==1.10.0`) |
| Health / readiness | Implemented |
| Domain foundation + replenishment aggregate | Implemented |
| Inventory ledger model | Implemented |
| Tenant-scoped Operator identity + authorization | Implemented |
| Tenant-scoped Product catalog | Implemented |
| Machine & physical slot configuration | Implemented |
| Inventory custody ledger + machine periods + sales consumption | Implemented |
| Repository / domain service Protocols | Implemented |
| Platform integration review | Implemented (V7; aligned to 1.10.0) |
| Platform `TransactionalUnitOfWork` + public `Database` | Implemented (consumed; composition helpers) |
| PostgreSQL domain persistence (ORM/repos/migrations) | Implemented (V8) |
| Business HTTP API (replenishment + inventory) | Implemented (V9) |
| Agent Core integration | Future |

## Outbox and UnitOfWork

Vending does **not** duplicate Outbox or UnitOfWork.

- Do **not** create `VendingUnitOfWork`.
- Do **not** use billing `UnitOfWork` for Vending domain writes.
- Use `TransactionalUnitOfWork` / `SqlAlchemyTransactionalUnitOfWork` and `DomainEvent` / `OutboxRecord` shapes.
- Details: [docs/architecture/PLATFORM_INTEGRATION.md](docs/architecture/PLATFORM_INTEGRATION.md).
