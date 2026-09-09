# ADR-015: Slot preferred product

- Status: Accepted
- Date: 2026-09-09

## Context

Operators need to know which SKU normally belongs in a slot, without freezing replenishment to that SKU.

## Decision

`preferred_product_id` is an optional configuration hint. It is not an operational restriction on what may be loaded during replenishment.

Application validates that a configured preferred product exists, is ACTIVE, and belongs to the same tenant.

## Consequences

- Planning/UI can show expected SKU.
- Replenishment remains free to apply its own substitution rules later.
- Catalog lifecycle (inactive products) is respected at configuration time.

## Alternatives considered

1. Preferred product hard-locks replenishment SKU — rejected for V5; belongs to replenishment policy.
2. No preferred product at all — rejected; loses useful configuration.
