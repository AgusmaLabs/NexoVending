# Replenishment rules — NexoVending

## Aggregate

- `Replenishment` is tenant-scoped (`tenant_id` from Machine) with required `idempotency_key`.
- Unique `(tenant_id, idempotency_key)`.
- Optimistic concurrency via `version`.
- Status: `IN_PROGRESS` → `COMPLETED` | `CANCELLED`.

## Lines

- Signed quantity: load (+) / unload (−).
- Capacity checked per operation against slot capacity.
- Preferred vs actual product: substitution allowed when prices match; price mismatch requires explicit handling.
- Historical `unit_price` and product description snapshot are stored on the line.

## Completion

- `CompleteReplenishment` writes ledger movements then marks COMPLETED in one transaction.
- Load → `REPLENISHMENT` (replenisher → slot).
- Unload → `SLOT_REMOVAL` (slot → replenisher).
- Movement idempotency keys: `{visit_key}:line:{line_id}`.
- Re-complete of an already COMPLETED visit is a no-op.

## Persistence

- Tables: `replenishments`, `replenishment_lines`.
- Uses Platform `TransactionalUnitOfWork` + Vending Session.
