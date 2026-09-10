# ADR-027: Transactional replenishment completion

- Status: Accepted
- Date: 2026-09-10

## Context

Completing a replenishment must update the visit and the inventory ledger together. Partial states (completed without movements, or movements without completion) are unacceptable.

## Decision

`CompleteReplenishment` is a single application transaction:

1. Load replenishment
2. For each line, record inventory movement (idempotent keys)
3. Mark replenishment COMPLETED
4. Commit via Platform `SqlAlchemyTransactionalUnitOfWork`

All writes share the injected Session.

## Consequences

- Rollback leaves visit `IN_PROGRESS` and ledger unchanged.
- Idempotent re-entry does not duplicate movements.
- See [TRANSACTION_BOUNDARY.md](../architecture/TRANSACTION_BOUNDARY.md).

## Alternatives considered

1. Separate commits for visit and ledger — rejected; partial failure window.
2. Database triggers — rejected; hides business rules.
