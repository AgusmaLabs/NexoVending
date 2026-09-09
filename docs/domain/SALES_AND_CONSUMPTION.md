# Sales & Consumption

## Snack

- `SnackSale` is recorded by machine + slot + quantity.
- `product_id` may be unknown; do not invent SKU attribution across substitutions.

## Coffee

- `CoffeeSale` requires a `Recipe` for the selection.
- Consumption expands ingredients × sold units.
- Reject missing recipe or insufficient ingredient stock.

## Separation from ledger

Sales calculate consumption effects; they are not universal product `InventoryMovement` entries by themselves.
