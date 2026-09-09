# ADR-022: Snack sales without product attribution

- Status: Accepted
- Date: 2026-09-09

## Context

Snack machines often report slot sales without reliable SKU after substitutions.

## Decision

`SnackSale` records machine, slot, and quantity. `product_id` is optional. Do not invent SKU distribution.

## Consequences

- Honest consumption totals per slot.
- SKU-level snack sales remain future/optional when telemetry supports it.

## Alternatives considered

1. Force SKU on every snack sale — rejected; invents data.
