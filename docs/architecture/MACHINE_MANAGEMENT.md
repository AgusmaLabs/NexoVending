# Machine Management — NexoVending

Status: **Implemented** (domain + application). Persistence adapters and HTTP API are **planned**.

## Purpose

Configure tenant-scoped vending machines and their physical slots.

```text
Machine / Slot  →  configuration
Replenishment   →  operational load (actual product, qty, applied price)
```

## Aggregate

```text
Tenant
  │
  └── Machine (Aggregate Root)
       ├── MachineId
       ├── MachineCode (tenant-unique)
       ├── MachineType: SNACK | COFFEE | MIXED
       ├── MachineStatus: ACTIVE | INACTIVE | MAINTENANCE
       ├── MachineLocation (configured address + geo)
       ├── SIIid (optional)
       └── MachineSlot[] (owned collection)
            ├── SlotId
            ├── slot_number (unique per machine)
            ├── capacity (mutable config ≠ stock)
            ├── preferred_product_id (optional hint)
            ├── selling_price (optional, slot-scoped)
            └── SlotStatus: ACTIVE | INACTIVE
```

`MachineType` does **not** restrict whether slots exist. SNACK, COFFEE, and MIXED may all have zero or more slots.

## Application

Tenant comes from Platform `RequestContext`. Use cases include create/update/lifecycle, add/activate/deactivate slots, change capacity, set/clear preferred product, set selling price, get/list/find-by-code.

Preferred product validation (same tenant + ACTIVE) is enforced in application when configuring a slot.

## Out of scope (V5)

Inventory/stock, replenishment operations, QR, GPS operacional, HTTP API, PostgreSQL machine tables.
