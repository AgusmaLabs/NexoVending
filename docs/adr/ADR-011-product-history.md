# ADR-011: Product history via soft deactivate

- Status: Accepted
- Date: 2026-09-09

## Context

Replenishment and inventory history must keep referring to products even after they leave the active catalog.

## Decision

Products are not hard-deleted as a business operation. They transition:

```text
ACTIVE → INACTIVE
```

and remain addressable by `ProductId` / barcode for historical snapshots.

## Consequences

- Catalog UI shows inactive items separately.
- Barcode remains reserved within the tenant while inactive (V4 rule).
- Future replenishment lines keep `product_description_snapshot` independent of later renames.

## Alternatives considered

1. Physical delete — rejected; breaks historical references.
2. Allow reusing barcode of inactive products immediately — deferred; V4 prefers unambiguous lookup.
