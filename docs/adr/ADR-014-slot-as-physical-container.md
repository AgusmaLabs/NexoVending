# ADR-014: Slot as physical container

- Status: Accepted
- Date: 2026-09-09

## Context

Slots could be modeled as fixed SKU assignments or as physical positions/containers.

## Decision

A `MachineSlot` represents a physical position/container with configurable capacity, optional preferred product, and optional selling price — not a rigid SKU lock.

## Consequences

- Supports snack spirals, coffee containers, and mixed layouts.
- Configuration can change without inventing a second aggregate.
- Actual loaded product remains a replenishment concern.

## Alternatives considered

1. Slot equals permanent product assignment — rejected; blocks substitutions and reconfiguration.
2. Slot only for snack machines — rejected; see ADR-013.
