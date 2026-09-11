# Inventory HTTP API

Status: **Implemented** (V9).

Base path: `/inventory`

| Method | Path | Permission | Entitlement |
| --- | --- | --- | --- |
| POST | `/inventory/assignments` | `inventory.assign` | `vending.inventory` |
| POST | `/inventory/returns` | `inventory.return` | `vending.inventory` |
| POST | `/inventory/adjustments` | `inventory.adjust` | `vending.inventory` |
| POST | `/inventory/losses` | `inventory.loss` | `vending.inventory` |
| GET | `/inventory/balance` | `inventory.read` | `vending.inventory` |
| GET | `/inventory/movements` | `inventory.read` | `vending.inventory` |

## Location query / body

```json
{
  "location_type": "REPLENISHER",
  "holder_id": "<operator-uuid>",
  "position_id": null
}
```

`MACHINE_SLOT` / `MACHINE_CONTAINER` require `position_id`.

Balance / movements use query params: `location_type`, `holder_id`, `product_id`, optional `position_id`.

Sales API is **out of scope** for V9.
