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
- `LineResolutionStatus`:
  - `resolved` — requires `product_id`; may generate inventory movements.
  - `pending_product_resolution` — `product_id` null, `manual_description` required; no substitution; no inventory until admin resolve.
- `resolve_line_product` only PENDING → RESOLVED; allowed on COMPLETED visits; rejected on CANCELLED; idempotent for same product.

## Completion

- `CompleteReplenishment` writes ledger movements **only for RESOLVED lines**, then marks COMPLETED in one transaction.
- PENDING lines remain on a COMPLETED visit until admin resolve.
- Load → `REPLENISHMENT` (replenisher → slot).
- Unload → `SLOT_REMOVAL` (slot → replenisher).
- Movement idempotency keys: `{visit_key}:line:{line_id}` (complete) or `{visit_key}:line:{line_id}:resolve` (deferred).
- Re-complete of an already COMPLETED visit is a no-op.

## Persistence

- Tables: `replenishments`, `replenishment_lines`.
- Uses Platform `TransactionalUnitOfWork` + Vending Session.
