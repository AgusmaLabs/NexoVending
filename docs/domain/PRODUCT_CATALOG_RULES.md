# Product Catalog Rules

### Creation

```text
tenant required (from RequestContext)
barcode required
name required
threshold >= 0
starts ACTIVE
```

### Identification

```text
ProductId = internal identity
Barcode = external/commercial identity
ProductId ≠ Barcode
```

### Lifecycle

```text
ACTIVE ↔ INACTIVE
inactive != deleted
```

### Tenant

```text
barcode uniqueness = tenant scoped
same barcode allowed across different tenants
```

### Unknown barcode

```text
unknown barcode does not create Product automatically
```

### History

```text
deactivated products remain addressable for replenishment/inventory history
```
