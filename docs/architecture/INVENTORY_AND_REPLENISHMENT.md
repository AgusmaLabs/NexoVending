# Inventory & Replenishment — NexoVending

Status: **Implemented** (domain + application + PostgreSQL persistence V8).

See [PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md), [TRANSACTION_BOUNDARY.md](TRANSACTION_BOUNDARY.md), [ADR-026](../adr/ADR-026-platform-persistence-integration.md), [ADR-027](../adr/ADR-027-transactional-replenishment-completion.md).

## Physical flow

```text
Purchase → Administrator → Assignment → Replenisher
    → Replenishment → Machine / Slot
    → Sale / Consumption → Inventory reconciliation
```

## Separation

| Concern | Meaning |
| --- | --- |
| Machine/Slot config | preferred product, capacity, selling price |
| Replenishment | actual load/unload, historical unit price, substitution reason |
| Inventory ledger | custody transfers and adjustments |
| Machine period | opening + replenishments − consumption → theoretical; physical → variance |
| Sales | Snack by slot (SKU optional); Coffee via recipe ingredients |

## Modules

- `domain.inventory` — movements, locations, ledger, custody, counts, periods
- `domain.replenishment` — aggregate, signed quantity, capacity, substitution
- `domain.sales` — snack/coffee sales and recipe consumption
- `application.inventory` / `application.replenishment` / `application.sales`

Domain does **not** import Platform, FastAPI, or SQLAlchemy.

Vending does not introduce a product-local UnitOfWork; V8 adapters share the Session from Platform `SqlAlchemyTransactionalUnitOfWork`.
