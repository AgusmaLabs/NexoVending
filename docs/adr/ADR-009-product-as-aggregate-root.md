# ADR-009: Product as aggregate root

- Status: Accepted
- Date: 2026-09-09

## Context

Vending needs a product catalog with clear identity, barcode uniqueness, and lifecycle without premature complexity.

## Decision

`Product` is the Aggregate Root. Do not introduce a `ProductCatalog` aggregate root unless transactional rules appear that require coordinating multiple products as one consistency boundary.

## Consequences

- Simple create/update/activate/deactivate flows.
- Uniqueness of `(tenant_id, barcode)` is enforced in application now and by PostgreSQL later.
- Catalog-wide policies can still live as domain/application services.

## Alternatives considered

1. `ProductCatalog` aggregate containing all products — rejected as unnecessary for V4.
2. Anemic product records mutated freely — rejected; weak invariants.
