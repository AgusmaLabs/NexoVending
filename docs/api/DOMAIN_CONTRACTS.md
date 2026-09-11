# Domain Contracts — NexoVending

Public-facing **domain/application contracts**. These are not HTTP APIs yet.

## Repository ports

```python
ProductRepository.get / save / find_by_barcode(tenant_id, barcode) / list_active(tenant_id)
InventoryRepository.record_movement / list_movements_for_location / expected_quantity
InventoryCountRepository.get / save
MachineInventoryPeriodRepository.get_open / save
ReplenishmentRepository.get / find_by_idempotency_key / save
OperatorRepository.get / save / find_by_principal(tenant_id, principal)
```

## Domain service ports

```python
ProductLookup.find_by_barcode(tenant_id, barcode) -> Product | None
InventoryAvailability.is_available(location, product_id, quantity) -> bool
```

## Application commands (catalog)

- `CreateProduct` — tenant from `RequestContext`; rejects duplicate barcode in tenant
- `UpdateProduct` — descriptive fields only; preserves `product_id` / `tenant_id`
- `ChangeProductBarcode` — explicit commercial identity change
- `ActivateProduct` / `DeactivateProduct` — soft lifecycle
- `FindProductByBarcode` — tenant-scoped lookup; unknown → `None` (no auto-create)

## Application commands (machines)

- `CreateMachine` / `UpdateMachine`
- `ActivateMachine` / `DeactivateMachine` / `PutMachineInMaintenance`
- `AddMachineSlot` / slot activate-deactivate / `ChangeSlotCapacity`
- `SetPreferredProduct` / `ClearPreferredProduct` / `SetSlotSellingPrice`
- `GetMachine` / `FindMachineByCode` / `ListMachineSlots`

## Application commands (replenishment / inventory / sales)

- `StartReplenishment` / `AddReplenishmentLine` / `CompleteReplenishment` / `CancelReplenishment`
- `RegisterInventoryMovement`
- `CreateInventoryCount` / `RecordInventoryCountLine` / `CompleteInventoryCount`
- `RegisterSnackSale` / `RegisterCoffeeSale`

## Status

| Contract | Status |
| --- | --- |
| Domain entities / VOs / errors | Implemented |
| Repository / service Protocols | Implemented |
| In-memory fakes (tests) | Implemented |
| PostgreSQL adapters | Implemented (V8) |
| HTTP / mobile adapters | Implemented (V9–V10) — see [MOBILE_API_CONTRACT.md](MOBILE_API_CONTRACT.md) |
