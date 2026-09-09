# Machine & Slot Domain Rules

Status: **Implemented**

## Machine

- Identity is `MachineId` (Vending-owned), independent of Platform identifiers.
- `MachineCode` is required, normalized, and unique within a tenant.
- Status transitions:
  - `INACTIVE → ACTIVE`
  - `ACTIVE → INACTIVE | MAINTENANCE`
  - `MAINTENANCE → ACTIVE | INACTIVE`
- Only `ACTIVE` machines may start replenishment (existing operational gate).
- Configured `MachineLocation` is not the GPS captured during a replenishment visit.

## MachineType vs slots

```text
MachineType does NOT determine whether slots may exist.
SNACK  → 0..N slots
COFFEE → 0..N slots
MIXED  → 0..N slots
```

## MachineSlot

- Represents a physical position/container, not a rigid SKU assignment.
- `slot_number > 0` and unique within the machine.
- `capacity > 0` and mutable (e.g. spiral change) without changing `SlotId` or `slot_number`.
- `capacity ≠ stock`. Stock remains an inventory concern.
- Slot lifecycle: `ACTIVE` / `INACTIVE`.

## Preferred product

- Optional configuration hint for the SKU normally expected in the slot.
- Does **not** restrict which product may be loaded during replenishment.
- When set via application, product must exist, belong to the same tenant, and be `ACTIVE`.

## Selling price

- Belongs to `MachineSlot` configuration, not the Product catalog.
- Independent per machine/slot for the same preferred product.
- Mutable; optional until pricing is configured.
