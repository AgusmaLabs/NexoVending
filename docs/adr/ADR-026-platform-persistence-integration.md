# ADR-026: Platform persistence integration

- Status: Accepted
- Date: 2026-09-09
- Updated: 2026-09-11 (`nexo-platform==1.10.0` — idempotency / flags / observability available)

## Context

V0–V6 delivered domain and application for identity, products, machines, inventory, replenishment, and sales against Protocol ports and in-memory fakes. Commit 6 deferred PostgreSQL wiring until answering:

1. How does Vending consume Platform’s database?
2. What Session / UnitOfWork exists?
3. How is request/tenant context resolved?
4. Where do repositories live?
5. How is the transaction implemented?
6. How are tenant boundaries modeled?

V7 review against `nexo-platform==1.2.0` found that the public `UnitOfWork` was billing-shaped and SQLAlchemy persistence lived under private modules. Vending therefore requested a generic transactional contract in Platform rather than inventing `VendingUnitOfWork`.

As of `nexo-platform==1.10.0`, published contracts relevant to Vending include:

- `TransactionalUnitOfWork` / `SqlAlchemyTransactionalUnitOfWork` (`nexo_platform.transaction`)
- `Database` / `SessionFactory` (`nexo_platform.persistence` public package)
- `RequestContext` / `TenantContext` / `TenantRef`
- `IdempotencyService` (1.8+), `FeatureFlags` (1.9+), `Observability` (1.10+) — for API/adapters
- Billing `UnitOfWork` remains a specialization (`nexo_platform.billing`)

## Decision

### 1. Database

- Vending owns domain schema via its own `DATABASE_URL` and Alembic migrations.
- Composition root obtains Engine/Session through **public** `Database.from_url(...)` / `SessionFactory`.
- Vending must **not** import `nexo_platform.persistence.database` internals (`Base`, module-level `engine` / `SessionLocal`) or private SQLAlchemy UoW modules.
- Products define their own `DeclarativeBase`; never inherit Platform `Base`.

### 2. Session

- Session is created by the product (via Platform `SessionFactory`) and injected into `SqlAlchemyTransactionalUnitOfWork(session)`.
- Application and Domain never import Session; only composition root and persistence adapters do.
- `uow.session is session` must hold.

### 3. Unit of Work / transactions

- Vending does **not** implement a parallel `VendingUnitOfWork`.
- Vending does **not** wire billing `UnitOfWork` / `BillingUnitOfWork` for inventory/replenishment.
- Vending uses `TransactionalUnitOfWork` + `SqlAlchemyTransactionalUnitOfWork` for commit / rollback / flush / nested rejection (`NestedTransactionError`).
- Reuse Platform `RetryPolicy` / `TransactionConflict` for reliability; do not reimplement them.
- Domain SQL adapters (V8) proceed on this contract; no further Platform structural gate.

### 4. Tenant / context

- Authoritative tenant: `TenantContext.from_request(RequestContext).require_tenant_id()`.
- Never trust client-supplied tenant id as authority.
- Application maps to domain `TenantId` and scopes repository calls.
- Persistence (V8): `tenant_id` columns, query filters, tenant-aware constraints; isolation tests required.

### 5. Repositories

- Ports stay as `Protocol`s in `domain/*/repositories.py`.
- SQLAlchemy adapters + ORM mappers live in Vending `infrastructure/persistence/` (V8).
- Multiple Vending repositories share the Session from the Platform UoW for multi-aggregate atomicity.

### 6. Events / Outbox

- Business events use Platform `DomainEvent` / `OutboxRecord` shapes.
- Outbox rows for Vending facts persist in **Vending** tables (same Session/transaction) unless a public Platform SQL outbox adapter is adopted later.
- Do not import private Platform outbox SQL wiring.

## Consequences

- ADR-001 §5: consume generic Platform transactional UoW; billing UoW is not that contract.
- Architecture guards allow `nexo_platform.persistence` and `nexo_platform.transaction` / `context` / `tenant`; forbid `persistence.database` and `persistence.sqlalchemy` internals.
- V8 implements Vending ORM/repos/migrations; does not wait on new Platform UoW work.
- See [PLATFORM_INTEGRATION.md](../architecture/PLATFORM_INTEGRATION.md).

## Alternatives considered

1. **Implement `VendingUnitOfWork`** — rejected; duplicates transversal infrastructure.
2. **Reuse billing `UnitOfWork` as-is** — rejected; wrong bounded context.
3. **Import private persistence SQLAlchemy modules** — rejected; breaks public-API-only rule.
4. **Keep custom `create_engine` forever** — rejected once Platform published `Database`; Vending wraps public `Database` in composition helpers.
