# ADR-017: Inventory ledger as source of truth

- Status: Accepted
- Date: 2026-09-09

## Context

Vending needs expected stock for administrators, replenishers, and machine positions without opaque balance fields.

## Decision

Use an immutable `InventoryMovement` ledger with explicit source/destination locations. Expected quantities are derived.

## Consequences

- Auditable custody chain.
- `SLOT_REMOVAL` and `LOSS` remain distinct.
- Persistence must later protect concurrent ledger updates.

## Alternatives considered

1. Mutable stock balances only — rejected; not auditable.
2. Artificial `OPENING_BALANCE` movements for periods — rejected for machine periods.
