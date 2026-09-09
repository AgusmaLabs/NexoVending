# ADR-018: Replenishment as aggregate

- Status: Accepted
- Date: 2026-09-09

## Context

Replenishment visits have lifecycle and line invariants that must stay consistent.

## Decision

`Replenishment` is the Aggregate Root owning `ReplenishmentLine`s. Terminal states cannot be modified.

## Consequences

- Clear visit lifecycle.
- Lines validated against machine slots inside the aggregate API.

## Alternatives considered

1. Standalone lines without aggregate — rejected; weak lifecycle.
