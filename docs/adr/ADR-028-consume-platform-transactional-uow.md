# ADR-028: Consume Platform TransactionalUnitOfWork

- Status: Accepted
- Date: 2026-09-10

## Context

V7 required a generic Platform UoW. Platform 1.3–1.10 published `TransactionalUnitOfWork` / `SqlAlchemyTransactionalUnitOfWork`, public `Database` / `SessionFactory`, and later Idempotency / FeatureFlags / Observability.

## Decision

NexoVending does **not** implement `VendingUnitOfWork`. Composition root:

```text
Database.from_url(DATABASE_URL)
  → Session
  → SqlAlchemyTransactionalUnitOfWork(session)
  → VendingPersistence.for_session(session)
```

Billing `UnitOfWork` is unused by Vending.

## Consequences

- Architecture tests allow `nexo_platform.persistence` / `transaction`; forbid private `persistence.database` / `persistence.sqlalchemy`.
- Nested UoW on the same Session raises `NestedTransactionError`.
- Optimistic conflicts raise Platform `TransactionConflict`.

## Alternatives considered

1. Product-local UoW — rejected (ADR-026).
2. Import private Platform SQLAlchemy UoW — rejected.
