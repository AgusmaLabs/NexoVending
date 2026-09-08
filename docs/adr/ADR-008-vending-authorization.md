# ADR-008: Vending authorization

- Status: Accepted
- Date: 2026-09-08

## Context

Being authenticated is not enough to replenish machines. Vending needs its own operational authorization.

## Decision

Platform authenticates. Vending authorizes.

```text
Authenticated → Principal → Resolve Operator → ACTIVE? → Role? → Validity? → Can Replenish
```

Policy `can_operator_replenish(operator, at)` requires:

- `status == ACTIVE`
- `role == OPERATOR`
- `validity_period.is_valid_at(at)` (`[from, until)`)

Admin capabilities (`can_manage_operators`, inventory, machines) remain separate from replenish.

## Consequences

- Authorization rules evolve in Vending without changing Platform auth.
- Application must resolve operator from context before business use cases.

## Alternatives considered

1. Map Platform roles directly to Vending permissions — rejected; product rules differ.
2. Authorize solely on JWT claims — rejected; ignores Vending lifecycle/validity.
