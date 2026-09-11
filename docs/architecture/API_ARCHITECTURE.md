# API architecture — NexoVending

Status: **Implemented** (V9 HTTP + V10 execution context + versioned `/api/v1`). Sales / Admin Web / Flutter client remain **planned**.

Canonical decision: [ADR-029](../adr/ADR-029-vending-http-api-boundary.md).  
Versioning: [VERSIONING.md](../VERSIONING.md), [ADR-031](../adr/ADR-031-http-api-and-package-versioning.md).

## Flow

```text
HTTP
  → FastAPI routers (thin) under /api/v1
  → Application use cases
  → Domain
  → Vending repositories (same Session)
  → Platform SqlAlchemyTransactionalUnitOfWork
  → PostgreSQL
```

Probes (`/health`, `/health/ready`) stay at the process root (unversioned).

Cross-cutting (Platform):

- `RequestContext` / `TenantContext`
- `AuthorizationService` + Vending permission codes
- `EntitlementService` + Vending entitlement codes
- `IdempotencyService.for_session` (mutating + `Idempotency-Key`)
- `Observability`

## Layout

```text
api/
  dependencies/   auth, access, database, wiring
  routers/        replenishments, inventory
  schemas/        HTTP DTOs
  error_handlers.py
  serializers.py
```

## Auth headers

| Header | Role |
| --- | --- |
| `Authorization: Bearer principal/<provider>/<subject>` | Trusted principal |
| `X-Tenant-Id` | Trusted tenant |
| `X-Request-Id` | Optional correlation |
| `Idempotency-Key` | Optional; mutating operations |

## Related

- [MOBILE_API_CONTRACT.md](../api/MOBILE_API_CONTRACT.md) — **canonical contract for Flutter / mobile**
- [REPLENISHMENT_API.md](../api/REPLENISHMENT_API.md)
- [MACHINES_API.md](../api/MACHINES_API.md)
- [PRODUCTS_API.md](../api/PRODUCTS_API.md)
- [INVENTORY_API.md](../api/INVENTORY_API.md)
- [ERRORS.md](../api/ERRORS.md)
- [IDEMPOTENCY.md](../api/IDEMPOTENCY.md)
- [PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md)
