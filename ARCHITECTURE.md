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
Forbidden in **domain**: any `nexo_platform` import.

## What belongs where

### Platform (dependency)

- Tenant / RequestContext
- UnitOfWork / Outbox mechanism
- Identity, authorization, entitlement, billing (as published)

### Vending (this product)

- Domain: products, machines/slots, inventory ledger, replenishment aggregate (**implemented**)
- Application use cases for replenishment (**implemented**)
- HTTP health API (**implemented**)
- Vending PostgreSQL schema for domain tables (**planned**)
- Business HTTP/mobile APIs (**planned**)

## Hexagonal layout

```text
api/                 FastAPI adapters (thin)
application/         use cases (Start/Add/Complete Replenishment)
domain/
  common/            IDs, VOs, errors
  identity/          Operator contract
  products/          Product + ports
  machines/          Machine, MachineSlot, MachineType
  inventory/         InventoryMovement + InventoryLedger
  replenishment/     Replenishment aggregate
infrastructure/      SQLAlchemy engine for health/readiness (domain persistence planned)
```

See also:

- [docs/architecture/PRODUCT_CATALOG.md](docs/architecture/PRODUCT_CATALOG.md)
- [docs/domain/PRODUCT_CATALOG_RULES.md](docs/domain/PRODUCT_CATALOG_RULES.md)

## Runtime

```text
Request
  │
  ▼
Tenant RequestContext (Platform)     ← Application only
  │
  ▼
Vending Application use cases
  │
  ▼
Domain aggregates / ledger
```

## Implemented vs planned

| Capability | Status |
| --- | --- |
| Package bootstrap + Platform dependency | Implemented (`nexo-platform==1.2.0`) |
| Health / readiness | Implemented |
| Domain foundation + replenishment aggregate | Implemented |
| Inventory ledger model | Implemented |
| Tenant-scoped Operator identity + authorization | Implemented |
| Tenant-scoped Product catalog | Implemented |
| Repository / domain service Protocols | Implemented |
| PostgreSQL domain persistence | Planned |
| Business HTTP API | Planned |
| Agent Core integration | Future |

## Outbox and UnitOfWork

Vending does **not** duplicate Outbox or UnitOfWork. Domain events will use Platform contracts when persistence lands.
