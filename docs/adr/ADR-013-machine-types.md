# ADR-013: Machine types

- Status: Accepted
- Date: 2026-09-09

## Context

Vending operates snack, coffee, and mixed machines. An earlier draft assumed coffee machines had no slots.

## Decision

`MachineType` is `SNACK | COFFEE | MIXED`. Type does **not** restrict whether a machine may have slots. All types support `0..N` slots.

Operational replenishment rules (e.g. coffee visit lines without slot) remain separate from machine configuration.

## Consequences

- Coffee machines can model physical containers when needed.
- Mixed machines share the same slot model.
- Replenishment policy stays free to evolve without rewriting configuration.

## Alternatives considered

1. Coffee machines cannot have slots — rejected; too rigid for mixed hardware.
2. Separate slot models per type — rejected; unnecessary duplication.
