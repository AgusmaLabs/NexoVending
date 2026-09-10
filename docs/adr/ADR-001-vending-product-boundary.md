# ADR-001: Vending as an independent product

- Status: Accepted
- Date: 2026-09-07
- Updated: 2026-09-10 (consume `nexo-platform==1.7.0` public UoW + Database)

## Context

NexoVending must digitalize vending replenishment operations. Historically, product code risked living inside the Platform monorepo (`src/products/vending`), which blurred ownership and made Platform depend conceptually on a business product.

After Platform extraction (P22), Platform is an installable package (`nexo-platform==1.0.0`) with a public API. Vending must consume that package as an external dependency.

## Decision

1. **Independent product repository / package**
   - Distribution: `nexo-vending`
   - Import package: `nexo_vending`
   - Depends on `nexo-platform==1.0.0` via pip (not path, not submodule, not copied sources).

2. **Dependency direction**
   - Allowed: Vending → Platform
   - Forbidden: Platform → Vending

3. **Public API only**
   - Vending may use `nexo_platform` top-level exports and documented capability packages (tenant, transaction, persistence `Database`/`SessionFactory`, identity, events, outbox, …).
   - Vending must not import Platform internals (e.g. `nexo_platform.persistence.database` private symbols, infrastructure modules, private domain trees).

4. **Data ownership**
   - Platform owns Platform tables/migrations.
   - Vending owns Vending tables/migrations and its own `DATABASE_URL`.

5. **Transaction / events**
   - Vending consumes Platform’s generic `TransactionalUnitOfWork` / `SqlAlchemyTransactionalUnitOfWork` plus `DomainEvent` / Outbox record shapes.
   - Public persistence lifecycle uses `Database` / `SessionFactory` (`nexo_platform.persistence`).
   - The billing-shaped `UnitOfWork` / `BillingUnitOfWork` is **not** the contract for inventory/replenishment.
   - Vending does not implement a parallel Outbox mechanism or a product-local `VendingUnitOfWork`.
   - See [ADR-026](ADR-026-platform-persistence-integration.md).

6. **API boundary**
   - FastAPI is a Vending adapter shell.
   - Business use cases live in Vending application/domain layers.

7. **Agent Core**
   - Deferred. V01 proves Vending → Platform first.
   - Future: Vending → Agent Core → Platform (as separate contracts).

## Consequences

- Clean install / Docker must resolve `nexo-platform` as a package (wheel/index), not via `PYTHONPATH` to Platform sources.
- Architecture tests guard copied Platform trees and forbidden imports from day one.
- Domain features (Machine, Inventory, Restock) arrive in later commits without revisiting the product boundary.
- Persistence (V8) implements Vending ORM/repos on top of Platform `Database` + `TransactionalUnitOfWork` ([ADR-026](ADR-026-platform-persistence-integration.md)).

## Alternatives considered

1. Keep Vending inside the Platform repository — rejected; couples product releases to Platform and invites reverse dependency.
2. Path dependency (`nexo-platform @ file://...`) — rejected for V01 acceptance; hides packaging failures.
3. Copy Platform modules into Vending — rejected; duplicates ownership and drifts.
4. Depend on Agent Core in V01 — rejected; obscures which layer provides which capability.
