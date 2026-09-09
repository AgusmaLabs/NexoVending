# Product Catalog — NexoVending

Status: **Implemented** (domain + application). Persistence adapters are **planned**.

## Map

```text
Tenant
  │
  └── Product Catalog
       │
       ├── Product (Aggregate Root)
       │    ├── ProductId
       │    ├── TenantId
       │    ├── Barcode
       │    ├── Name
       │    ├── Description
       │    ├── Brand
       │    ├── Category
       │    ├── Unit
       │    ├── Low Stock Threshold
       │    └── Status (ACTIVE | INACTIVE)
       │
       └── Product Lookup (tenant + barcode)
```

## Scan flow

```text
Barcode scan
     ↓
FindProductByBarcode (RequestContext.tenant_id)
     ↓
Product found?
   ┌─┴─┐
  yes  no
   │    │
   ▼    ▼
Product  Unknown barcode → Replenishment manual_description
         (does NOT auto-create Product)
```

## Rules

- Tenant comes from Platform `RequestContext`, never client payload authority.
- Barcode uniqueness is tenant-scoped (including inactive products in V4).
- Soft deactivate only — no business hard delete.
- `ProductId ≠ Barcode`.
- Replenishment should snapshot `product_description_snapshot` (contract for V7).
