# Inventory rules — NexoVending

## Ledger

- Stock is derived from immutable `InventoryMovement` rows (location-based deltas).
- `Quantity` on a movement is always **positive**; direction comes from source/destination locations.
- Types: `ASSIGNMENT`, `REPLENISHMENT`, `SLOT_REMOVAL`, `RETURN`, `ADJUSTMENT`, `LOSS`.
- Negative stock at a source location is rejected (`InsufficientStockError`).
- Optional `idempotency_key` is unique per `tenant_id` (partial unique index).

## Custody

- Administrator / Replenisher / Machine slot|container are location types.
- Assignments credit replenisher custody; replenishment completion debits replenisher and credits slots.

## Counts

- Physical counts compute variance; they **never** auto-create `LOSS`.

## Persistence

- Table: `inventory_movements`.
- Repositories share the Session from Platform `SqlAlchemyTransactionalUnitOfWork`.
