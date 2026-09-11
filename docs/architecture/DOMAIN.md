# Domain Model — NexoVending

Status: **Implemented** (domain + PostgreSQL persistence V8). HTTP API planned (V9).

## Map

```text
                    VENDING DOMAIN
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
   Replenishment     Inventory          Sales
        │                │                 │
        │          ┌─────┴─────┐      ┌────┴─────┐
        │     Administrator Replenisher Snack   Coffee
        │                                │       │
        └───────────────┐                │    Recipe
                     Machine ────────────┘
                        │
                 Inventory Period / Count
```

## Bounded contexts (modules)

| Module | Responsibility |
| --- | --- |
| `domain.common` | IDs, value objects, domain errors |
| `domain.identity` | Operator lifecycle, validity, Vending authorization policies |
| `domain.products` | Tenant-scoped Product aggregate, barcode lookup, catalog lifecycle |
| `domain.machines` | Machine aggregate, physical slots, types/status, pricing/preferred SKU config |
| `domain.inventory` | Location ledger, custody, counts, machine periods |
| `domain.replenishment` | Replenishment aggregate, signed qty, capacity, substitution |
| `domain.sales` | Snack/coffee sales and recipe consumption |

## Key invariants

- Inactive / non-ACTIVE machines cannot start replenishment.
- Machine configuration: any `MachineType` may have `0..N` slots; preferred product is a hint; capacity ≠ stock.
- Replenishment lines use signed quantity with per-operation capacity `0 < abs(qty) <= capacity`.
- Substitution keeps preferred product unchanged; requires reason + matching configured price.
- Completed / cancelled replenishments cannot accept new lines.
- Custody stock is derived from immutable location movements; variance never auto-creates `LOSS`.
- Machine theoretical stock uses period opening + replenishments − consumption.
- Snack sales may omit SKU; coffee sales expand recipes into ingredient consumption.
- Domain timestamps must be timezone-aware.
- Domain does **not** import FastAPI, SQLAlchemy, or `nexo_platform` (except `domain.identity` → Platform auth contracts).

## Application use cases

- Replenishment: `StartReplenishment`, `AddReplenishmentLine`, `CompleteReplenishment`, `CancelReplenishment`
- Inventory: `RegisterInventoryMovement`, inventory count create/record/complete
- Sales: `RegisterSnackSale`, `RegisterCoffeeSale`
- Machines / Products / Identity: as in prior commits

Tenant / actor context enters through Application (from Platform `RequestContext` where applicable), not through Domain entities.
