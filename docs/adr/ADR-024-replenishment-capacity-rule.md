# ADR-024: Replenishment capacity rule

- Status: Accepted
- Date: 2026-09-09

## Context

Between visits, sales reduce physical stock; capacity is a physical load limit per operation.

## Decision

Enforce `0 < abs(quantity) <= capacity` per line. Do not use `current_stock + quantity <= capacity`. Repeated `+capacity` operations are valid.

## Consequences

- Matches field reality.
- Avoids false rejects after sales.

## Alternatives considered

1. Cumulative capacity against theoretical stock — rejected.
