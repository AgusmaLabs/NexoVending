# ADR-023: Coffee sales and recipe consumption

- Status: Accepted
- Date: 2026-09-09

## Context

Coffee machines consume ingredients via selections/recipes, not single SKU slot sales.

## Decision

`CoffeeSale` expands a `Recipe` into ingredient consumptions scaled by sold units. Reject missing recipes or insufficient ingredient stock.

## Consequences

- Multiple consumptions per sale.
- Clear separation from snack sale model.

## Alternatives considered

1. Treat coffee like snack slot sales — rejected; wrong inventory model.
