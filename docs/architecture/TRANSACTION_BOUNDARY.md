# Transaction boundary — NexoVending

Status: **Implemented** (`nexo-platform==1.7.0`). Domain multi-aggregate adapters use Platform UoW (V8).

## Rule

```text
Platform SqlAlchemyTransactionalUnitOfWork
        = transaction lifecycle (commit / rollback / flush / nested guard)

Vending use cases
        = business transaction orchestration

Vending repositories
        = persistence on the injected Session
```

Do not implement a second generic UoW in Vending.

## Pattern

```python
from nexo_platform.persistence import Database
from nexo_platform.transaction import SqlAlchemyTransactionalUnitOfWork

db = Database.from_url(database_url)
session = db.session_factory()()
try:
    async with SqlAlchemyTransactionalUnitOfWork(session) as uow:
        assert uow.session is session
        # load aggregates / write via Vending repos sharing `session`
        await uow.flush()  # optional; not a commit
finally:
    session.close()
```

## Semantics

| Path | Effect |
| --- | --- |
| Success exit from `async with` | flush + commit |
| Exception | rollback |
| Commit failure | rollback + re-raise |
| Nested UoW on same Session | `NestedTransactionError` |

`flush()` does **not** commit.

## CompleteReplenishment (V8)

Atomic unit:

```text
Replenishment state change
+
InventoryMovement writes
```

same Session, one Platform UoW.

## Related

- [PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md)
- [ADR-026](../adr/ADR-026-platform-persistence-integration.md)
- NexoPlatform `docs/TRANSACTIONS.md`
