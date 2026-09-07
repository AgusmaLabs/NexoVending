# ADR-003: Inventory ledger

- Status: Accepted
- Date: 2026-09-07

## Context

Operator stock must be auditable: assignments, replenishments, returns, losses, and adjustments need a clear history.

## Decision

Stock is **derived** from immutable `InventoryMovement` records:

```text
stock =
    SUM(ASSIGNMENT) + SUM(RETURN) + SUM(ADJUSTMENT)
  - SUM(REPLENISHMENT) - SUM(LOSS)
```

Never treat `UPDATE stock SET quantity = …` as the source of truth.

Domain rejects movements that would produce negative stock. Concurrent lost-update prevention is owned by persistence (future).

## Consequences

- Full audit trail and reconciliation become natural.
- Reads of current stock require aggregation (or a projection later).
- Persistence commit must enforce uniqueness / locking for races.

## Alternatives considered

1. Mutable quantity field as source of truth — rejected; weak audit.
2. Event sourcing for the whole product — deferred; ledger is enough for V1 inventory.
