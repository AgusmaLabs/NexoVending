# ADR-019: Product substitution on replenishment

- Status: Accepted
- Date: 2026-09-09

## Context

Slots have preferred products that may be unavailable during visits.

## Decision

Allow substituting another product when `replacement_reason` is set and `unit_price` matches configured slot selling price. Do not mutate `preferred_product_id`. Snapshot preferred product and reason on the line.

## Consequences

- Operational flexibility without rewriting configuration.
- Historical audit of substitutions.

## Alternatives considered

1. Auto-change preferred product — rejected.
2. Forbid all substitutions — rejected as too rigid.
