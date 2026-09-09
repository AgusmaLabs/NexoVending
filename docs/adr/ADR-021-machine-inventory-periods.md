# ADR-021: Machine inventory periods

- Status: Accepted
- Date: 2026-09-09

## Context

Machine stock is not continuously known; periods close with physical counts.

## Decision

`MachineInventoryPeriod` tracks opening, replenishment net, consumption, physical quantity, and variance. Initial opening is 0 without an `OPENING_BALANCE` movement. Next opening equals previous physical.

## Consequences

- Clear theoretical vs physical model.
- Variance investigation remains explicit.

## Alternatives considered

1. Always-known machine stock balances — rejected for snack reality.
