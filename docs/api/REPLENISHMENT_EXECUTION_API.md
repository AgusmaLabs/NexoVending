# Replenishment execution HTTP flow

Paths are relative to `/api/v1`.

```text
GET  /machines/resolve
POST /replenishments          (+ location / accuracy_m)
GET  /machines/{id}/slots
GET  /products/barcode/{code}
POST /replenishments/{id}/lines   # RESOLVED or PENDING + manual_description
POST /replenishments/{id}/complete  # movements only for RESOLVED lines
# Admin later:
GET  /replenishments/pending-product-resolutions
POST /replenishments/{id}/lines/{line_id}/resolve-product
```

Create body may use `accuracy` or `accuracy_m`. Official `started_at` is server-controlled when omitted.

Pending lines: `product_id` null + required `manual_description`; no auto-create product (ADR-032).

Mutating calls use Platform `Idempotency-Key` + UoW as in V9.
