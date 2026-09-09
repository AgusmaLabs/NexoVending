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
| `domain.machines` | Machine, MachineSlot, MachineType |
| `domain.inventory` | InventoryMovement + InventoryLedger |
| `domain.replenishment` | Replenishment aggregate + lines |

## Key invariants

- Inactive machines cannot start replenishment.
- Snack lines require `slot > 0`; coffee lines forbid slot.
- Quantity must be `> 0`.
- Unknown products require `manual_description`; known products keep `product_description_snapshot`.
- Completed / cancelled replenishments cannot accept new lines.
- Stock is derived from immutable movements; never `stock = N` as source of truth.
- Domain timestamps must be timezone-aware.
- Domain does **not** import FastAPI, SQLAlchemy, or `nexo_platform`.

## Application use cases (V2)

- `StartReplenishment`
- `AddReplenishmentLine`
- `CompleteReplenishment`

Tenant / actor context enters through Application (from Platform `RequestContext`), not through Domain entities.
