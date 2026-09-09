# ADR-020: Historical replenishment pricing

- Status: Accepted
- Date: 2026-09-09

## Context

Slot selling price can change after a visit.

## Decision

Store `unit_price` on `ReplenishmentLine` as the historical applied price. Never reconstruct history from current slot price. Inventory is not valued from this price in V6.

## Consequences

- Correct operational history.
- Pricing changes remain configuration concerns.

## Alternatives considered

1. Always read current slot price — rejected; loses history.
