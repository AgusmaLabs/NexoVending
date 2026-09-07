# ADR-004: Replenishment as aggregate root

- Status: Accepted
- Date: 2026-09-07

## Context

Replenishment visits have strict invariants (machine status, snack/coffee slot rules, quantities, product identity, lifecycle).

## Decision

`Replenishment` is the **aggregate root**. Lines are only created through:

- `add_line(...)`
- `complete(...)`
- `cancel(...)`

External code must not mutate `lines` directly. The aggregate stores `machine_type` at start time so slot rules do not require leaking Machine internals into callers.

`idempotency_key` is part of the aggregate; uniqueness is enforced later by persistence.

## Consequences

- Invariants stay centralized.
- Application use cases orchestrate repositories and call aggregate methods.
- Future offline sync can rely on idempotency keys.

## Alternatives considered

1. Anemic lines mutated from services — rejected; easy to bypass rules.
2. Separate aggregates per line — rejected; lifecycle is visit-scoped.
