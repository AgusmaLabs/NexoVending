# ADR-010: Barcode identity

- Status: Accepted
- Date: 2026-09-09

## Context

Scanners identify commercial products by barcode, but aggregates need stable technical IDs independent of packaging changes.

## Decision

```text
ProductId ≠ Barcode
```

Barcode is a normalized commercial identifier (`Barcode` value object). Uniqueness is:

```text
tenant_id + barcode
```

Barcode changes use an explicit `ChangeProductBarcode` use case, not generic update.

## Consequences

- Lookups are always tenant-scoped.
- Same barcode may exist in different tenants.
- Persistence will later add a unique constraint matching this rule (including inactive rows in V4).

## Alternatives considered

1. Use barcode as primary key — rejected; brittle when packaging codes change.
2. Global unique barcode across tenants — rejected; breaks multi-tenant isolation.
