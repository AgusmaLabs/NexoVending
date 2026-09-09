# Domain Model — NexoVending

Status: **Implemented** (in-memory domain foundation). Persistence adapters are **planned**.

## Map

```text
                 VENDING DOMAIN

       ┌───────────────┐
       │    Product    │
       └───────┬───────┘
               │
┌──────────────▼──────────────┐
│           Machine           │
│                             │
│ ┌─────────────┐             │
│ │ MachineSlot │             │
│ └─────────────┘             │
└──────────────┬──────────────┘
               │
               ▼
      ┌─────────────────┐
      │  Replenishment  │  ← aggregate root
      │                 │
      │ ┌─────────────┐ │
      │ │    Lines    │ │
      │ └─────────────┘ │
      └────────┬────────┘
               │
               ▼
      InventoryMovement (immutable ledger)
```

## Bounded contexts (modules)

| Module | Responsibility |
| --- | --- |
| `domain.common` | IDs, value objects, domain errors |
| `domain.identity` | Operator lifecycle, validity, Vending authorization policies |
| `domain.products` | Tenant-scoped Product aggregate, barcode lookup, catalog lifecycle |
| `domain.machines` | Machine aggregate, physical slots, types/status, pricing/preferred SKU config |
| `domain.inventory` | InventoryMovement + InventoryLedger |
| `domain.replenishment` | Replenishment aggregate + lines |

## Key invariants

- Inactive / non-ACTIVE machines cannot start replenishment.
- Machine configuration: any `MachineType` (SNACK/COFFEE/MIXED) may have `0..N` slots; preferred product is a hint, not a load lock; capacity ≠ stock.
- Snack replenishment lines require `slot > 0`; coffee replenishment lines forbid slot (operational rule, separate from machine slot configuration).
- Quantity must be `> 0`.
- Unknown products require `manual_description`; known products keep `product_description_snapshot`.
- Completed / cancelled replenishments cannot accept new lines.
- Stock is derived from immutable movements; never `stock = N` as source of truth.
- Domain timestamps must be timezone-aware.
- Domain does **not** import FastAPI, SQLAlchemy, or `nexo_platform` (except `domain.identity` → Platform auth contracts).

## Application use cases

- Replenishment: `StartReplenishment`, `AddReplenishmentLine`, `CompleteReplenishment`
- Machines: create/update/lifecycle, slot configuration (capacity, preferred product, selling price)

Tenant / actor context enters through Application (from Platform `RequestContext`), not through Domain entities.
