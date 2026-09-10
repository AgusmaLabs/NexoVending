# Commit 7 — `docs(architecture): platform integration review before persistence`

## 1. Objetivo

Documentar la **revisión de integración con NexoPlatform (V7)** y fijar las decisiones de DB, Session, Unit of Work, tenant y repositorios **antes** de implementar persistencia de dominio (V8).

Este commit es **solo documentación**. No implementa adapters SQL, migraciones de dominio, ni cambios en NexoPlatform.

## 2. Alcance

### Incluido

* Respuestas a las 6 preguntas de commit 6 §27.
* ADR-026 (Platform persistence integration).
* Enmienda ADR-001 §5 (UoW genérico vs billing).
* Enmienda ADR-005 (tenant_id en entidades + enforcement V8).
* `docs/architecture/PLATFORM_INTEGRATION.md` con el **spec** de `TransactionalUnitOfWork` a publicar en Platform.
* Actualización de `ARCHITECTURE.md`, `DEPENDENCIES.md`, inventario, índice de arquitectura.
* Secuencia: V7 marcado; V8 explícitamente gated.

### Fuera de alcance

* Implementar `TransactionalUnitOfWork` en NexoPlatform (workspace aparte).
* Bump de `nexo-platform` en Vending.
* ORM models / Alembic de dominio / repository adapters.
* HTTP API de negocio.
* Idempotencia / concurrencia / Testcontainers de dominio.

## 3. Decisiones clave

```text
DB          → owned by Vending (DATABASE_URL + Alembic); no Platform private engine
Session     → owned by Vending; bind vía contrato público Platform
UoW         → TransactionalUnitOfWork genérico en Platform (NO VendingUnitOfWork;
              NO billing UnitOfWork)
Tenant      → RequestContext → Application → TenantId / filtros / constraints V8
Repos      → Protocols en domain; adapters SQL en infrastructure (V8)
```

Orden obligatorio:

```text
V7 (este commit)
  → NexoPlatform: TransactionalUnitOfWork
  → publish / version
  → Vending bump
  → V8 Persistence
```

## 4. Artefactos

| Artefacto | Rol |
| --- | --- |
| [ADR-026](../adr/ADR-026-platform-persistence-integration.md) | Decisiones + gate V8 |
| [PLATFORM_INTEGRATION.md](../architecture/PLATFORM_INTEGRATION.md) | Spec de capacidad Platform + resumen operativo |
| [ADR-001](../adr/ADR-001-vending-product-boundary.md) | §5 enmendado |
| [ADR-005](../adr/ADR-005-tenant-isolation.md) | tenant_id actualizado |
| [ARCHITECTURE.md](../../ARCHITECTURE.md) | Estado V7 / bloqueo V8 |
| [secuencia.md](secuencia.md) | V7 done; V8 gated |

## 5. Criterios de aceptación

1. Las 6 preguntas de commit 6 §27 tienen respuesta explícita en ADR-026 + PLATFORM_INTEGRATION.md.
2. Queda escrito que **no** se implementa UoW propio en Vending.
3. Queda escrito el contrato mínimo que debe publicar Platform.
4. Queda escrito que **V8 no arranca** sin bump de `nexo-platform` con ese contrato.
5. ADR-001 ya no trata el UoW billing como el contrato genérico de producto.
6. ADR-005 refleja `tenant_id` en agregados tenant-scoped.
7. **No** hay adapters PostgreSQL de dominio ni migraciones de tablas de negocio en este commit.
8. **No** se modifica NexoPlatform desde este workspace.

## 6. Definition of Done

```text
[x] ADR-026 created
[x] PLATFORM_INTEGRATION.md created (TransactionalUnitOfWork spec)
[x] ADR-001 §5 amended
[x] ADR-005 amended
[x] ARCHITECTURE.md updated
[x] DEPENDENCIES.md updated
[x] INVENTORY_AND_REPLENISHMENT.md notes V7/V8 gate
[x] architecture index links PLATFORM_INTEGRATION.md
[x] secuencia.md marks V7 done; V8 gated

[ ] Platform TransactionalUnitOfWork NOT implemented here
[ ] nexo-platform bump NOT done here
[ ] Domain PostgreSQL adapters NOT implemented
[ ] Domain Alembic tables NOT added
[ ] VendingUnitOfWork NOT introduced
```

## 7. Siguiente paso

1. ~~En el workspace **NexoPlatform**: implementar y publicar `TransactionalUnitOfWork`~~ — **hecho** (`nexo-platform` 1.3–1.7; ver `docs/TRANSACTIONS.md` / `PERSISTENCE.md`).
2. ~~En **NexoVending**: bump de dependencia~~ — **hecho** (`nexo-platform==1.7.0`).
3. **V8 Persistence**: ORM, migraciones, repository adapters, atomicidad multi-agregado sobre `SqlAlchemyTransactionalUnitOfWork`.
