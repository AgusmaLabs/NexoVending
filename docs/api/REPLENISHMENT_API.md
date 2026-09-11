# Replenishment HTTP API

Status: **Implemented** (V9 + V11 pending product resolution).

API prefix: `/api/v1`. Base path below: `/replenishments`.

| Method | Path | Permission | Entitlement |
| --- | --- | --- | --- |
| POST | `/replenishments` | `replenishment.create` | `vending.replenishment` |
| GET | `/replenishments/{id}` | `replenishment.read` | `vending.replenishment` |
| POST | `/replenishments/{id}/lines` | `replenishment.add_line` | `vending.replenishment` |
| POST | `/replenishments/{id}/complete` | `replenishment.complete` | `vending.replenishment` |
| POST | `/replenishments/{id}/cancel` | `replenishment.cancel` | `vending.replenishment` |
| GET | `/replenishments/pending-product-resolutions` | `replenishment.resolve_product` | `vending.replenishment` |
| POST | `/replenishments/{id}/lines/{line_id}/resolve-product` | `replenishment.resolve_product` | `vending.replenishment` |

## Create

```json
{
  "machine_id": "<uuid>",
  "location": { "latitude": -33.4, "longitude": -70.6, "accuracy": 5.0 },
  "started_at": "2026-09-11T12:00:00+00:00"
}
```

`Idempotency-Key` recommended. Tenant is **not** accepted in the body.

## Add line

```json
{
  "slot_id": "<uuid>",
  "product_id": "<uuid>",
  "quantity": 8,
  "replacement_reason": "OUT_OF_STOCK"
}
```

`unit_price` optional — defaults from slot selling price. Capacity / substitution validated in domain.

## Complete

Runs `CompleteReplenishment` inside one Platform UoW (replenishment + inventory movements). Prefer `Idempotency-Key` for retries.

OpenAPI: `/docs`.
