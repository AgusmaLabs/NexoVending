# Mobile API Contract — NexoVending

Status: **Implemented** (V9 HTTP + V10 execution context + V11 unresolved product).  
Audience: Flutter / mobile developers integrating with NexoVending.  
Source of truth: `src/nexo_vending/api/` (OpenAPI also at `/docs` when the server runs).

Related docs: [API_ARCHITECTURE.md](../architecture/API_ARCHITECTURE.md), [REPLENISHMENT_EXECUTION_CONTEXT.md](../architecture/REPLENISHMENT_EXECUTION_CONTEXT.md), [ERRORS.md](ERRORS.md), [IDEMPOTENCY.md](IDEMPOTENCY.md).

---

## 1. What this contract is

NexoVending exposes a **backend HTTP API** for the replenisher operational flow and for inventory administration.

```text
Mobile app
   │  captures: QR, GPS, barcode, slot, quantity
   ▼
NexoVending HTTP API
   │  authenticates, authorizes, validates business rules
   ▼
Application / Domain / PostgreSQL
```

**Rule:** the mobile app captures data; **Vending decides** if the operation is valid. Do not re-implement capacity, stock, tenant, or assignment rules on the client as authority.

---

## 2. Base URL and discovery

| Item | Value |
| --- | --- |
| HTTP API version | `v1` |
| Business base path | `/api/v1` — **all paths in §4–§8 are relative to this prefix** |
| Package version | `0.2.0` (backend deploy / OpenAPI `info.version`; not a mobile pip dep) |
| Liveness | `GET /health` (unversioned; returns `package_version` + `api_version`) |
| Readiness (DB) | `GET /health/ready` |
| OpenAPI UI | `GET /docs` |
| OpenAPI JSON | `GET /openapi.json` |
| Offline OpenAPI | `python scripts/export_openapi.py --out docs/api/openapi-v1.json` |

Example absolute URL: `https://api.example.com/api/v1/machines/resolve`.

Configure the **host** in the mobile environment; keep `/api/v1` as the API base path. Do not hardcode tenant or operator IDs as trust sources.

Versioning policy: [VERSIONING.md](../VERSIONING.md), [ADR-031](../adr/ADR-031-http-api-and-package-versioning.md).

---

## 3. Authentication and context (every business call)

Health endpoints need **no** auth. All other endpoints require:

| Header | Required | Format / meaning |
| --- | --- | --- |
| `Authorization` | **Yes** | `Bearer principal/<provider>/<subject>` |
| `X-Tenant-Id` | **Yes** | Trusted tenant id (from gateway / session), **never** from free-form user input as authority |
| `X-Request-Id` | No | Correlation id; echoed in error `request_id` when present |
| `Idempotency-Key` | Recommended on **POST** | Opaque string; same key + same payload → same result |

### Example

```http
Authorization: Bearer principal/google/118234567890
X-Tenant-Id: tenant-acme
X-Request-Id: 01JMOBILE-REQ-001
Idempotency-Key: 01JMOBILE-CREATE-R1
```

### Auth semantics

1. The bearer token is a **trusted principal** already authenticated by a gateway (or test harness). Vending does **not** implement OAuth/JWT login for mobile in this version.
2. Vending resolves `Principal` + `X-Tenant-Id` → `Operator` for that tenant.
3. If the operator is missing / wrong tenant / inactive for the action → **403**.
4. Missing credentials or tenant → **401** with FastAPI shape `{"detail":"..."}` (not the domain error envelope).

### Never send as authority in JSON body

- `tenant_id`
- `operator_id` / `actor_id` (server uses the authenticated operator)

---

## 4. Inventory of exposed endpoints

Full business URLs = `/api/v1` + path below (e.g. `POST /api/v1/replenishments`).

### 4.1 Health (no auth)

| Method | Path | Success | Response |
| --- | --- | ---: | --- |
| GET | `/health` | 200 | `status`, `package_version`, `api_version` |
| GET | `/health/ready` | 200 | same + readiness — or **503** if DB unavailable |

### 4.2 Machines (replenisher)

Entitlement: `vending.replenishment`. Requires an **effective machine assignment** for the acting replenisher (except where noted).

| Method | Path | Permission | Success |
| --- | --- | --- | ---: |
| GET | `/machines/resolve` | `machine.resolve` | 200 |
| GET | `/machines/{machine_id}` | `machine.read` | 200 |
| GET | `/machines/{machine_id}/slots` | `machine.read` | 200 |

### 4.3 Products (capture lookup)

| Method | Path | Permission | Entitlement | Success |
| --- | --- | --- | --- | ---: |
| GET | `/products/barcode/{barcode}` | `product.read` | `vending.replenishment` | 200 |

### 4.4 Replenishments (core mobile flow)

Entitlement: `vending.replenishment`. Mutating routes also require an ACTIVE **OPERATOR** (not ADMIN) within validity.

| Method | Path | Permission | Success |
| --- | --- | --- | ---: |
| POST | `/replenishments` | `replenishment.create` | **201** |
| GET | `/replenishments/{id}` | `replenishment.read` | 200 |
| POST | `/replenishments/{id}/lines` | `replenishment.add_line` | 200 |
| POST | `/replenishments/{id}/complete` | `replenishment.complete` | 200 |
| POST | `/replenishments/{id}/cancel` | `replenishment.cancel` | 200 |

### 4.4b Admin product resolution (not typical replenisher UX)

Requires ADMIN + `replenishment.resolve_product`:

| Method | Path | Permission | Success |
| --- | --- | --- | ---: |
| GET | `/replenishments/pending-product-resolutions` | `replenishment.resolve_product` | 200 |
| POST | `/replenishments/{id}/lines/{line_id}/resolve-product` | `replenishment.resolve_product` | 200 |

### 4.5 Inventory (admin / back-office style)

Entitlement: `vending.inventory`. Mutations require **ADMIN** (`can_manage_inventory`). Typical replenisher mobile apps may **not** call these.

| Method | Path | Permission | Success |
| --- | --- | --- | ---: |
| POST | `/inventory/assignments` | `inventory.assign` | **201** |
| POST | `/inventory/returns` | `inventory.return` | **201** |
| POST | `/inventory/adjustments` | `inventory.adjust` | **201** |
| POST | `/inventory/losses` | `inventory.loss` | **201** |
| GET | `/inventory/balance` | `inventory.read` | 200 |
| GET | `/inventory/movements` | `inventory.read` | 200 |

**Total business + health routes: 19.**

---

## 5. Canonical replenisher flow

Use this sequence on the mobile app:

```text
1. Resolve machine (QR or internal id)
2. Optional: GET slots (capacity, preferred product, current qty)
3. POST /replenishments  (send GPS)
4. For each physical load/unload:
      scan barcode → GET /products/barcode/{code}
      POST /replenishments/{id}/lines
5. POST /replenishments/{id}/complete
   (or cancel if aborted)
```

Diagram:

```text
Scan QR
  → GET /machines/resolve?identifier_type=QR_CODE&value=MIX-001
  → machine_id, slots summary

POST /replenishments
  { machine_id, location: { latitude, longitude, accuracy_m } }
  → replenishment_id (status IN_PROGRESS)

GET /machines/{machine_id}/slots
  → choose slot_id

Scan barcode
  → GET /products/barcode/7801234
  → product_id   OR 404 if unknown

POST /replenishments/{id}/lines
  { slot_id, product_id, quantity }
  → updated replenishment with lines

POST /replenishments/{id}/complete
  → status COMPLETED (+ inventory movements server-side)
```

---

## 6. Endpoint contracts (request / response)

### 6.1 Resolve machine

`GET /machines/resolve?identifier_type={type}&value={value}`

| Query | Values |
| --- | --- |
| `identifier_type` | `QR_CODE` (machine operational code) or `INTERNAL_ID` (UUID) |
| `value` | Code or UUID string |

**200 `MachineOut`**

```json
{
  "machine_id": "…",
  "identifier": "MIX-001",
  "machine_type": "SNACK",
  "name": "Lobby",
  "status": "ACTIVE",
  "slots": [
    {
      "slot_id": "…",
      "slot_number": 7,
      "capacity": 10,
      "status": "ACTIVE",
      "preferred_product_id": "…",
      "selling_price": "1500",
      "current_quantity": null
    }
  ]
}
```

Notes:

- On resolve/get, `current_quantity` is always `null`.
- Use `/machines/{id}/slots` for operational quantities.
- Unknown QR / no access → **404** or **403** (`MACHINE_ACCESS_DENIED`).

### 6.2 Get machine / slots

`GET /machines/{machine_id}` → same `MachineOut` shape (assignment required).

`GET /machines/{machine_id}/slots` →

```json
{
  "machine_id": "…",
  "slots": [
    {
      "slot_id": "…",
      "slot_number": 7,
      "capacity": 10,
      "status": "ACTIVE",
      "preferred_product_id": "…",
      "selling_price": "1500",
      "current_quantity": 4
    }
  ]
}
```

`current_quantity` is inventory for the **preferred product** at that slot (or `null` if no preferred product).

Distinguish:

| Field | Meaning |
| --- | --- |
| `preferred_product_id` | Slot **configuration** |
| Line `product_id` on replenishment | Product **actually loaded** |

### 6.3 Product by barcode

`GET /products/barcode/{barcode}`

**200**

```json
{
  "product_id": "…",
  "barcode": "7800001",
  "name": "Coca",
  "status": "ACTIVE",
  "unit": "CAN"
}
```

**404** if not in this tenant’s catalog — the backend **never** auto-creates a product.

Mobile UX for unknown barcode (client-side): rescan → optional manual description path only if the backend contract for that line allows it; prefer resolving a real `product_id`.

### 6.4 Create replenishment

`POST /replenishments` → **201**

```json
{
  "machine_id": "…",
  "location": {
    "latitude": -35.4264,
    "longitude": -71.6554,
    "accuracy_m": 12.4
  }
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `machine_id` | yes | From resolve |
| `location.latitude` / `longitude` | yes | Valid geo ranges |
| `location.accuracy` or `accuracy_m` | no | Alias accepted; omitted → `0.0` |
| `started_at` | no | Server uses UTC now if omitted |

Send **`Idempotency-Key`**. If omitted, server uses `replenishment.create:{request_id}`.

GPS is **captured and stored**. It does **not** geofence in this version.

Response: `ReplenishmentOut` (see §6.8). Status starts as `IN_PROGRESS`.

### 6.5 Add replenishment line

`POST /replenishments/{id}/lines` → **200**

**Resolved (catalog product known):**

```json
{
  "slot_id": "…",
  "product_id": "…",
  "quantity": 8,
  "replacement_reason": "OUT_OF_STOCK"
}
```

**Pending product resolution (barcode 404 or unreadable; V11):**

```json
{
  "slot_id": "…",
  "quantity": 5,
  "barcode": "123456789",
  "manual_description": "Bebida energética X",
  "product_id": null
}
```

| Field | Required | Notes |
| --- | --- | --- |
| `slot_id` | yes | Must belong to the replenishment’s machine |
| `quantity` | yes | Positive = load; negative = unload; must respect capacity |
| `product_id` | for RESOLVED | From barcode lookup when known |
| `barcode` | optional | Lookup path; unknown + `manual_description` → PENDING |
| `manual_description` | for PENDING | Required when product identity is unknown |
| `replacement_reason` | if substituting | Only on RESOLVED lines |
| `unit_price` | no | Defaults to slot `selling_price` |
| `scanned_at` | no | Server UTC now if omitted |

After barcode **404**: retry scan in UX; if still unknown, require `manual_description` and POST a PENDING line (`product_id` null, `resolution_status=pending_product_resolution`). Complete is allowed with pending lines; machine stock by SKU is incomplete until admin resolve.

Server validates (examples):

- replenishment `IN_PROGRESS`
- slot on machine
- RESOLVED: product exists in tenant + replenisher stock for loads
- PENDING: no replenisher stock check; no `replacement_reason`
- quantity vs slot capacity

Failures → **409** with codes such as `CAPACITY_EXCEEDED`, `INSUFFICIENT_INVENTORY`, `SUBSTITUTION_REJECTED`, `INVALID_STATE`.

### 6.6 Complete / cancel

`POST /replenishments/{id}/complete`  
Body optional: `{ "completed_at": "…" }` (ISO-8601). Prefer `Idempotency-Key`.

`POST /replenishments/{id}/cancel`  
Body optional: `{ "cancelled_at": "…" }`.

Complete runs **atomically**: replenishment status + inventory movements in one Platform transaction.

### 6.7 Get replenishment

`GET /replenishments/{id}` → `ReplenishmentOut`. Cross-tenant → **404**.

### 6.8 `ReplenishmentOut` shape

```json
{
  "id": "…",
  "machine_id": "…",
  "operator_id": "…",
  "status": "IN_PROGRESS",
  "machine_type": "SNACK",
  "started_at": "2026-09-11T15:00:00+00:00",
  "completed_at": null,
  "location": { "latitude": -35.42, "longitude": -71.65, "accuracy": 12.4 },
  "idempotency_key": "…",
  "version": 1,
  "lines": [
    {
      "id": "…",
      "slot_id": "…",
      "product_id": "…",
      "quantity": 8,
      "unit_price": "1500",
      "occurred_at": "…",
      "product_description_snapshot": "Coca",
      "preferred_product_id_snapshot": "…",
      "replacement_reason": null,
      "barcode_scanned": "7800001",
      "manual_description": null
    }
  ]
}
```

`status`: `IN_PROGRESS` | `COMPLETED` | `CANCELLED`.

---

## 7. Inventory endpoints (admin)

Use when building admin/back-office mobile or shared clients. Replenisher field apps typically skip these.

### Locations

```json
{
  "location_type": "REPLENISHER",
  "holder_id": "<operator-uuid>",
  "position_id": null
}
```

| `location_type` | `holder_id` | `position_id` |
| --- | --- | --- |
| `ADMINISTRATOR` | operator UUID | omit |
| `REPLENISHER` | operator UUID | omit |
| `MACHINE_SLOT` | machine UUID | **required** slot UUID |
| `MACHINE_CONTAINER` | machine UUID | **required** container UUID |

### Assign / return / adjust / loss

See OpenAPI schemas under `/docs`. All mutating inventory POSTs accept `Idempotency-Key`.

### Balance / movements

```http
GET /inventory/balance?location_type=REPLENISHER&holder_id=…&product_id=…
GET /inventory/movements?location_type=REPLENISHER&holder_id=…&product_id=…
```

---

## 8. Errors

### Domain / business envelope (most 403/404/409)

```json
{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "insufficient replenisher inventory: need 5, have 3",
    "request_id": "…"
  }
}
```

### Auth / FastAPI shapes

| HTTP | Shape | When |
| ---: | --- | --- |
| 401 | `{"detail":"missing credentials"}` | No/invalid Authorization or missing `X-Tenant-Id` |
| 403 | `{"detail":"permission denied"}` / entitlement | Platform permission/entitlement gate |
| 422 | FastAPI validation | Bad JSON / types |
| 503 | `{"detail":"…"}` | `/health/ready` only |

### Codes mobile should handle

| Code | HTTP | Client action |
| --- | ---: | --- |
| `NOT_FOUND` | 404 | Show “not found”; do not retry as create |
| `MACHINE_ACCESS_DENIED` | 403 | Operator not assigned / cannot operate machine |
| `OPERATOR_NOT_FOUND` | 403 | Principal not provisioned for tenant |
| `CAPACITY_EXCEEDED` | 409 | Reduce quantity / choose another slot |
| `INSUFFICIENT_INVENTORY` | 409 | Cannot load more than replenisher stock |
| `SUBSTITUTION_REJECTED` | 409 | Provide valid `replacement_reason` or preferred product |
| `INVALID_STATE` | 409 | Replenishment not `IN_PROGRESS` / machine inactive |
| `IDEMPOTENCY_KEY_REUSE` | 409 | Same key, different payload — generate new key |
| `IDEMPOTENCY_IN_PROGRESS` | 409 | Retry later with same key |
| `TRANSACTION_CONFLICT` | 409 | Optimistic lock — reload and retry |

Never expect stack traces in responses.

---

## 9. Idempotency (mandatory for offline-friendly UX)

| Operation | Header |
| --- | --- |
| Create replenishment | `Idempotency-Key` **strongly recommended** |
| Add line | `Idempotency-Key` recommended |
| Complete / cancel | `Idempotency-Key` **strongly recommended** |
| Inventory POSTs | `Idempotency-Key` recommended |

Rules:

1. Same tenant + operation + key + **same payload hash** → replay previous result (no duplicate business effect).
2. Same key + **different** payload → `409 IDEMPOTENCY_KEY_REUSE`.
3. Generate keys on device (UUID / ULID). Persist until the server acknowledges success.
4. Do **not** invent a second client-side ledger as source of truth; server domain keys also protect complete/movements.

---

## 10. Permissions the mobile identity needs

For a **replenisher field app**, the Platform grants (per tenant + actor) should include:

```text
vending.replenishment          (entitlement)

machine.resolve
machine.read
product.read
replenishment.create
replenishment.read
replenishment.add_line
replenishment.complete
replenishment.cancel
```

Additionally the operator must:

- exist in Vending for that tenant + principal
- be ACTIVE with role **OPERATOR**
- have an **ACTIVE machine assignment** for each machine they work on

Admin inventory permissions (`inventory.*` + `vending.inventory`) are separate.

---

## 11. Explicitly out of scope (do not expect these HTTP APIs yet)

| Capability | Status |
| --- | --- |
| Flutter / offline SQLite sync | Not in Vending API |
| OAuth / Google Sign-In inside Vending | Gateway responsibility |
| Product catalog CRUD | Application only (no HTTP) |
| Create/update machines & slots | Application only |
| Assign machine ↔ replenisher | Application only (admin provisioning) |
| Sales / coffee recipes | Not exposed |
| Geofencing (“must be within 50m”) | Not enforced (location is stored only) |
| Push notifications / WhatsApp | Not exposed |
| Auto-create product from unknown barcode | **Forbidden** by design |

---

## 12. Mobile implementation checklist

- [ ] Send `Authorization` + `X-Tenant-Id` on every business call  
- [ ] Never put `tenant_id` in JSON as authority  
- [ ] Resolve machine before creating replenishment  
- [ ] Persist `Idempotency-Key` for create / line / complete  
- [ ] Treat barcode 404 as “unknown product”, not as create  
- [ ] On unknown/unreadable barcode: require `manual_description` and POST PENDING line  
- [ ] Allow complete with pending lines; do not invent `product_id`  
- [ ] Prefer `product_id` from lookup when adding RESOLVED lines  
- [ ] Show 409 codes with actionable UX (capacity, stock, substitution)  
- [ ] Use `/machines/{id}/slots` for layout + current qty  
- [ ] Treat cross-tenant misses as 404  
- [ ] Use ISO-8601 timestamps with timezone when sending datetimes  

---

## 13. Versioning note

This contract reflects the current NexoVending HTTP surface (**V9 + V10 + V11**). Breaking changes will be documented in ADRs / API docs and should bump OpenAPI accordingly. Prefer consuming OpenAPI (`/openapi.json`) in CI for client codegen, and treat this markdown as the human-readable mobile contract.
