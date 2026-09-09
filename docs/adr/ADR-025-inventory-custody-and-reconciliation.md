# ADR-025: Inventory custody and reconciliation

- Status: Accepted
- Date: 2026-09-09

## Context

Expected book inventory and physical counts must not be conflated; variances need investigation.

## Decision

Derive expected custody inventory from movements. Use `InventoryCount` for physical verification. Variance never auto-creates `LOSS`; loss requires an explicit movement.

## Consequences

- Clean audit path: detect → investigate → adjust/lose.
- Administrator and replenisher share the same reconciliation pattern.

## Alternatives considered

1. Auto-post LOSS from variance — rejected; premature and opaque.
