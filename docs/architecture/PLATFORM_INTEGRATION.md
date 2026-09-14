# Platform Integration — NexoVending

Status: **Aligned with `nexo-platform==1.11.0`**.  
V8 domain persistence uses Platform `Database` + `SqlAlchemyTransactionalUnitOfWork`.  
V9 HTTP should also consume Platform **Idempotency**, **Observability**, and (where needed) **FeatureFlags** — do not reimplement them in Vending.

Canonical decision record: [ADR-026](../adr/ADR-026-platform-persistence-integration.md).  
Platform references: `docs/PLATFORM_PUBLIC_API.md`, `PLATFORM_CONSUMER_GUIDE.md`, `TRANSACTIONS.md`, `PERSISTENCE.md`, `CONTEXT.md`, `TENANT_ISOLATION.md`, `IDEMPOTENCY.md`, `FEATURE_FLAGS.md`, `OBSERVABILITY.md`, `VERSIONING.md`.

## Answers to the pre-persistence questions

| Question | Decision |
| --- | --- |
| How does Vending consume Platform’s database? | It does **not** share Platform table ownership. Vending owns Alembic + domain schema. Session/Engine come from public `Database` / `SessionFactory` bound to Vending’s `DATABASE_URL`. |
| What Session / UnitOfWork exists? | `SqlAlchemyTransactionalUnitOfWork(session)` implementing `TransactionalUnitOfWork`. Session is product-injected; UoW does not create another Session. |
| How is context resolved? | Platform `RequestContext` + `TenantContext.from_request(context).require_tenant_id()`; never client payload as authority. |
| Where do repositories live? | Ports in `domain/*/repositories.py`; SQL adapters in `infrastructure/persistence/` (V8). |
| How is the transaction implemented? | `async with SqlAlchemyTransactionalUnitOfWork(session)`; Vending repos share that Session. |
| How are tenant limits modeled? | `tenant_id` on business rows + repo filters + DB constraints; authority from `RequestContext` / `TenantContext`. |

## What Vending consumes today (`nexo-platform==1.11.0`)

| Capability | Since | Public import | Vending use |
| --- | --- | --- | --- |
| Tenant / request | 1.5+ | `RequestContext`, `TenantContext`, `TenantRef` | Application binding / isolation |
| Identity | 1.1+ | `nexo_platform.identity.authentication` | Principal → Operator |
| Authorization / entitlement | 1.6+ | `AuthorizationService`, `Permission`, `EntitlementService`, … | Operator access (V9 API) |
| Persistence | 1.4+ | `Database`, `SessionFactory` | Composition root Session lifecycle |
| Transactions | 1.3+ | `TransactionalUnitOfWork`, `SqlAlchemyTransactionalUnitOfWork` | Commit / rollback / flush / nested guard |
| Reliability | — | `RetryPolicy`, `TransactionConflict`, `NestedTransactionError` | Concurrent writes |
| Events / outbox shapes | — | `DomainEvent`, `Outbox`, `OutboxRecord` | Business event form |
| Idempotency | **1.8+** | `IdempotencyKey`, `IdempotencyService`, … | **Wired** in V9 mutating HTTP |
| Feature flags | **1.9+** | `FeatureFlag`, `FeatureFlags`, `InMemoryFeatureFlags` | **Available** — optional product toggles |
| Observability | **1.10+** | `Logger`, `Metrics`, `Tracer`, `Observability` | **Wired** in V9 API adapters |

## Composition (current + V9)

```text
Vending Composition Root
        │
        ├── Database.from_url(DATABASE_URL)   # Platform public API
        ├── Session = session_factory()()
        ├── RequestContext / TenantContext
        ├── Authorization / Entitlement (V9)
        ├── FeatureFlags (optional)
        ├── Observability (V9)
        ├── Vending repositories (same Session)
        ├── SqlAlchemyTransactionalUnitOfWork(session)
        └── IdempotencyService.for_session(session)   # V9 mutating HTTP
```

```python
from nexo_platform.persistence import Database
from nexo_platform.tenant import TenantContext
from nexo_platform.transaction import SqlAlchemyTransactionalUnitOfWork
from nexo_platform.idempotency import IdempotencyKey, IdempotencyService
from nexo_platform.observability import Observability

db = Database.from_url(database_url)
session = db.session_factory()()
obs = Observability.noop()  # or .memory() in tests
try:
    tenant_id = TenantContext.from_request(context).require_tenant_id()
    async with SqlAlchemyTransactionalUnitOfWork(session) as uow:
        assert uow.session is session
        idempotency = IdempotencyService.for_session(uow.session)
        # Vending repo writes / protected mutating handlers…
finally:
    session.close()
    db.dispose()
```

## What Vending must not use

- `nexo_platform.persistence.database` internals (`Base`, module-level `engine` / `SessionLocal`)
- `nexo_platform.persistence.sqlalchemy…` (private)
- Billing `UnitOfWork` / `BillingUnitOfWork` for inventory/replenishment
- A parallel `VendingUnitOfWork`, local retry/idempotency store, or vendor observability SDKs in domain/application
- Client-supplied `tenant_id` as isolation authority

## Capability status

| Item | Status |
| --- | --- |
| `TransactionalUnitOfWork` / `SqlAlchemyTransactionalUnitOfWork` | Consumed (V8) |
| Public `Database` / `SessionFactory` | Consumed (V8) |
| Vending domain SQL adapters | Implemented (V8) |
| Platform Idempotency / FeatureFlags / Observability | Idempotency + Observability **wired in V9 API**; FeatureFlags available |
| Dependency pin | **`nexo-platform==1.11.0`** (`vendor/nexo_platform-1.11.0-*.whl`) |
| V9 HTTP replenishment / inventory | **Implemented** |

### Idempotency note

Domain already stores business keys (e.g. replenishment `idempotency_key`, movement keys). Platform `IdempotencyService` is the **HTTP/command** retry layer (`UNIQUE (tenant_id, operation, key)` in Platform tables). Both may coexist: Platform protects the request; domain keys protect ledger/visit effects. Prefer Platform service at the API boundary (V9) instead of inventing a second store.

Platform owns migration `platform_idempotency_records`. If Vending shares a PostgreSQL instance, run Platform migrations for that schema; do not copy the table into Vending Alembic.

## Ownership summary

| Concern | Owner |
| --- | --- |
| Tenant / auth / authz / entitlement / idempotency / flags / observability contracts | Platform |
| Generic transactional UoW + public Database | Platform |
| Billing UoW | Platform (unused by Vending) |
| Vending `DATABASE_URL` / Alembic / domain tables | Vending |
| Vending repository Protocols + SQL adapters | Vending |
| Inventory / replenishment / sales rules | Vending domain |

## Related docs

- [ADR-001](../adr/ADR-001-vending-product-boundary.md)
- [ADR-005](../adr/ADR-005-tenant-isolation.md)
- [ADR-026](../adr/ADR-026-platform-persistence-integration.md)
- [ADR-028](../adr/ADR-028-consume-platform-transactional-uow.md)
- [DEPENDENCIES.md](DEPENDENCIES.md)
- [TRANSACTION_BOUNDARY.md](TRANSACTION_BOUNDARY.md)
- [INVENTORY_AND_REPLENISHMENT.md](INVENTORY_AND_REPLENISHMENT.md)
