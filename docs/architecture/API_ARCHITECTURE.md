# API architecture — NexoVending

Status: **Implemented** (V9). Sales / Admin / Flutter remain **planned**.

Canonical decision: [ADR-029](../adr/ADR-029-vending-http-api-boundary.md).

## Flow

```text
HTTP
  → FastAPI routers (thin)
  → Application use cases
  → Domain
  → Vending repositories (same Session)
  → Platform SqlAlchemyTransactionalUnitOfWork
  → PostgreSQL
```

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

- [REPLENISHMENT_API.md](../api/REPLENISHMENT_API.md)
- [INVENTORY_API.md](../api/INVENTORY_API.md)
- [ERRORS.md](../api/ERRORS.md)
- [IDEMPOTENCY.md](../api/IDEMPOTENCY.md)
- [PLATFORM_INTEGRATION.md](PLATFORM_INTEGRATION.md)
