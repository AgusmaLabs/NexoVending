# Domain Contracts — NexoVending

Public-facing **domain/application contracts**. These are not HTTP APIs yet.

## Repository ports

```python
ProductRepository.get / save / find_by_barcode(tenant_id, barcode) / list_active(tenant_id)
MachineRepository.get / find_by_code(tenant_id, code) / save / list_by_tenant(tenant_id)
ReplenishmentRepository.get / find_by_idempotency_key / save
InventoryRepository.get_stock / record_movement / list_movements
OperatorRepository.get / save / find_by_principal(tenant_id, principal)
```

## Domain service ports

```python
ProductLookup.find_by_barcode(tenant_id, barcode) -> Product | None
InventoryAvailability.is_available(operator_id, product_id, quantity) -> bool
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

## Application commands (replenishment)

- `StartReplenishment` / `AddReplenishmentLine` / `CompleteReplenishment`

## Status

| Contract | Status |
| --- | --- |
| Domain entities / VOs / errors | Implemented |
| Repository / service Protocols | Implemented |
| In-memory fakes (tests) | Implemented |
| PostgreSQL adapters | Planned |
| HTTP / mobile adapters | Planned |
