# Replenishment execution HTTP flow

Paths are relative to `/api/v1`.

```text
GET  /machines/resolve
POST /replenishments          (+ location / accuracy_m)
GET  /machines/{id}/slots
GET  /products/barcode/{code}
POST /replenishments/{id}/lines
POST /replenishments/{id}/complete
```

Create body may use `accuracy` or `accuracy_m`. Official `started_at` is server-controlled when omitted.

Mutating calls use Platform `Idempotency-Key` + UoW as in V9.
