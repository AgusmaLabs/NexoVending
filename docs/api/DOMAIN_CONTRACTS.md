# Domain Contracts — NexoVending

Public-facing **domain/application contracts** for V2. These are not HTTP APIs yet.

## Repository ports

```python
ProductRepository.get / find_by_barcode / save
MachineRepository.get / get_by_code / save
ReplenishmentRepository.get / find_by_idempotency_key / save
InventoryRepository.get_stock / record_movement / list_movements
```

## Domain service ports

```python
ProductLookup.find_by_barcode(barcode) -> Product | None
InventoryAvailability.is_available(operator_id, product_id, quantity) -> bool
```

## Application commands

### StartReplenishment

Input: `operator_id`, `machine_id`, `started_at`, `geo_location`, `idempotency_key`  
Output: `Replenishment` (`IN_PROGRESS`)  
Idempotent on `idempotency_key`.

### AddReplenishmentLine

Input: `replenishment_id`, barcode / product identity, `quantity`, `slot?`, `manual_description?`, `scanned_at`  
Output: updated `Replenishment`

### CompleteReplenishment

Input: `replenishment_id`, `completed_at`  
Output: `Replenishment` (`COMPLETED`)

## Status

| Contract | Status |
| --- | --- |
| Domain entities / VOs / errors | Implemented |
| Repository / service Protocols | Implemented |
| In-memory fakes (tests) | Implemented |
| PostgreSQL adapters | Planned |
| HTTP / mobile adapters | Planned |
