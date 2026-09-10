# Platform Integration — NexoVending

Status: **Aligned with `nexo-platform==1.7.0`**. Generic transactional UoW, public `Database`, and **V8 domain persistence** (ORM/repos/migrations) are in place.

Canonical decision record: [ADR-026](../adr/ADR-026-platform-persistence-integration.md).  
Platform references (NexoPlatform workspace): `docs/TRANSACTIONS.md`, `docs/PERSISTENCE.md`, `docs/CONTEXT.md`, `docs/TENANT_ISOLATION.md`, `docs/PLATFORM_CONSUMER_GUIDE.md`, `docs/PLATFORM_PUBLIC_API.md`.

## Answers to the pre-persistence questions

| Question | Decision |
| --- | --- |
| How does Vending consume Platform’s database? | It does **not** share Platform table ownership. Vending owns Alembic + domain schema. Session/Engine come from public `Database` / `SessionFactory` bound to Vending’s `DATABASE_URL`. |
| What Session / UnitOfWork exists? | `SqlAlchemyTransactionalUnitOfWork(session)` implementing `TransactionalUnitOfWork`. Session is product-injected; UoW does not create another Session. |
| How is context resolved? | Platform `RequestContext` + `TenantContext.from_request(context).require_tenant_id()`; never client payload as authority. |
| Where do repositories live? | Ports in `domain/*/repositories.py`; SQL adapters in `infrastructure/persistence/` (V8). |
| How is the transaction implemented? | `async with SqlAlchemyTransactionalUnitOfWork(session)`; Vending repos share that Session. |
| How are tenant limits modeled? | `tenant_id` on business rows + repo filters + DB constraints (V8); authority from `RequestContext` / `TenantContext`. |

## What Vending consumes today (`nexo-platform==1.7.0`)

| Capability | Public import | Use |
| --- | --- | --- |
| Tenant / request | `RequestContext`, `TenantContext`, `TenantRef` | Application binding / isolation key |
| Identity | `nexo_platform.identity.authentication` | Principal → Operator |
| Authorization / entitlement | `AuthorizationService`, `Permission`, `EntitlementService`, … | Operator access (as needed) |
| Persistence | `Database`, `SessionFactory` from `nexo_platform.persistence` | Composition root Session lifecycle |
| Transactions | `TransactionalUnitOfWork`, `SqlAlchemyTransactionalUnitOfWork` | Commit / rollback / flush / nested guard |
| Reliability | `RetryPolicy`, `TransactionConflict`, `NestedTransactionError` | Concurrent writes (V8+) |
| Events / outbox shapes | `DomainEvent`, `Outbox`, `OutboxRecord` | Business event form |

## Composition (target for V8)

```text
Vending Composition Root
        │
        ├── Database.from_url(DATABASE_URL)   # Platform public API
        ├── Session = session_factory()()
        ├── RequestContext / TenantContext
        ├── Vending repositories (same Session)
        └── SqlAlchemyTransactionalUnitOfWork(session)
```

```python
from nexo_platform.persistence import Database
from nexo_platform.tenant import TenantContext
from nexo_platform.transaction import SqlAlchemyTransactionalUnitOfWork

db = Database.from_url(database_url)
session = db.session_factory()()
try:
    tenant_id = TenantContext.from_request(context).require_tenant_id()
    async with SqlAlchemyTransactionalUnitOfWork(session) as uow:
        assert uow.session is session
        # Vending repo writes…
finally:
    session.close()
    db.dispose()
```

## What Vending must not use

- `nexo_platform.persistence.database` internals (`Base`, module-level `engine` / `SessionLocal`)
- `nexo_platform.persistence.sqlalchemy…` (private)
- Billing `UnitOfWork` / `BillingUnitOfWork` for inventory/replenishment
- A parallel `VendingUnitOfWork`
- Client-supplied `tenant_id` as isolation authority

## Capability status (was V7 request)

| Item | Status |
| --- | --- |
| `TransactionalUnitOfWork` Protocol | **Delivered** (1.3.0+) |
| `SqlAlchemyTransactionalUnitOfWork` | **Delivered** (public) |
| Session injection by product | **Delivered** |
| Public `Database` / `SessionFactory` | **Delivered** (1.4.0+) |
| Billing UoW as specialization | **Delivered** |
| Vending domain SQL adapters | **Implemented** (V8) |
| Dependency pin in this product | **`nexo-platform==1.7.0`** |

V8 domain persistence is implemented on these contracts (`infrastructure/persistence`, migration `0002_vending_domain`).

| Concern | Owner |
| --- | --- |
| Tenant / auth / authz / entitlement context | Platform |
| Generic transactional UoW + public Database | Platform |
| Billing UoW | Platform (specialization; unused by Vending) |
| Vending `DATABASE_URL` / Alembic / domain tables | Vending |
| Vending repository Protocols | Vending domain |
| Vending SQL adapters / mappers | Vending infrastructure (V8) |
| Inventory / replenishment / sales rules | Vending domain |

## Related docs

- [ADR-001](../adr/ADR-001-vending-product-boundary.md)
- [ADR-005](../adr/ADR-005-tenant-isolation.md)
- [ADR-026](../adr/ADR-026-platform-persistence-integration.md)
- [DEPENDENCIES.md](DEPENDENCIES.md)
- [INVENTORY_AND_REPLENISHMENT.md](INVENTORY_AND_REPLENISHMENT.md)
- [TRANSACTION_BOUNDARY.md](TRANSACTION_BOUNDARY.md) (when present)
