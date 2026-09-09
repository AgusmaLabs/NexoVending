# Inventory Rules

- Ledger of `InventoryMovement` is the source of truth for **expected** custody stock.
- Locations: `ADMINISTRATOR`, `REPLENISHER`, `MACHINE_SLOT`, `MACHINE_CONTAINER`.
- Movement types: `ASSIGNMENT`, `REPLENISHMENT`, `SLOT_REMOVAL`, `RETURN`, `ADJUSTMENT`, `LOSS`.
- `SLOT_REMOVAL` ≠ `LOSS` (relocation vs confirmed loss).
- Quantity on movements is strictly positive; direction comes from source/destination.
- Expected inventory is derived; physical inventory requires an `InventoryCount`.
- Completing a count records variance but does **not** auto-create `LOSS`.
