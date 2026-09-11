# ADR-032 — Deferred product resolution on replenishment

## Context

In the field, a replenisher may load a product that is not in the tenant catalog or whose barcode is unreadable. The business needs to record slot, quantity, and a human clue, but the inventory ledger requires `product_id`.

## Decision

1. Allow `ReplenishmentLine` in status `PENDING_PRODUCT_RESOLUTION` with `product_id = null` and required `manual_description`.
2. `CompleteReplenishment` generates inventory movements only for `RESOLVED` lines.
3. Admin resolves via `ResolveReplenishmentLineProduct` using an existing catalog `Product` (no auto-create).
4. Deferred movements are written in the resolve transaction when the visit is already `COMPLETED`.
5. Resolve while `IN_PROGRESS` only updates the line; complete later writes the standard `:line:{id}` movement.

## Consequences

- Machine stock by SKU may lag physical reality until admin review.
- Field audit remains on the pending line (`manual_description`, optional barcode).
- Ledger integrity is preserved: no `InventoryMovement` without `product_id`.

## Alternatives considered

1. Block replenishment without product — rejected; does not match operations.
2. Auto-create `Product` from description — rejected (ADR-030).
3. `InventoryMovement` without `product_id` — rejected; breaks the ledger.
4. Generic incident without a replenishment line — rejected; loses visit/slot/quantity linkage.
