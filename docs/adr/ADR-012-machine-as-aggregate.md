# ADR-012: Machine as aggregate root

- Status: Accepted
- Date: 2026-09-09

## Context

Machines own physical slots with invariants that depend on the machine (unique slot numbers, tenant ownership, lifecycle, configuration).

## Decision

`Machine` is the Aggregate Root. `MachineSlot` is an entity inside that aggregate. There is no `MachineSlotRepository`.

## Consequences

- Slot mutations go through `Machine`.
- Consistency boundary is the machine document/transaction later in persistence.
- Simpler application orchestration for configuration use cases.

## Alternatives considered

1. Separate `MachineRepository` + `MachineSlotRepository` — rejected; splits slot uniqueness and ownership.
2. Flat slot table without aggregate semantics — rejected; weak invariants.
