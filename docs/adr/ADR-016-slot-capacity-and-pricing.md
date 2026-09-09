# ADR-016: Slot capacity and pricing

- Status: Accepted
- Date: 2026-09-09

## Context

Physical capacity (e.g. spiral size) and selling price vary by machine and slot, and can change over time independently of the product catalog.

## Decision

1. **Capacity** is mutable configuration on `MachineSlot`. Changing it does not change slot identity (`SlotId` / `slot_number`). Capacity is not stock.
2. **Selling price** belongs to the Machine/Slot configuration context, not the Product catalog. Prices may differ across machines for the same preferred product.

## Consequences

- Spiral/container changes are modeled without recreating slots.
- Catalog remains free of per-machine pricing.
- Stock tracking stays in inventory (planned/operational elsewhere).

## Alternatives considered

1. Capacity equals current stock — rejected; conflates config and inventory.
2. Price on Product only — rejected; cannot express machine-specific pricing.
