# Commit 11 — Unresolved Product on Replenishment

**Commit message**

`feat(replenishment): support unresolved product lines with deferred inventory`

## 1. Objetivo

Cerrar el gap entre el flujo del PRD (producto desconocido → descripción manual → revisión admin) y la implementación actual, donde:

```text
GET /products/barcode/{barcode}
       ↓
404
       ↓
manual_description (sugerido por contrato/PRD)
       ↓
POST /replenishments/{id}/lines
       ↓
DomainError: replenishment line requires a resolved product_id
```

V11 implementa el flujo completo de **línea pendiente de resolución de producto**, sin inventar SKUs ni escribir inventario sin identidad de producto.

Este commit establece la frontera entre:

```text
Observación operativa en campo
        ↓
Línea PENDING_PRODUCT_RESOLUTION
        ↓
Complete visita (movimientos solo para líneas resueltas)
        ↓
Resolución administrativa
        ↓
Movimientos de inventario diferidos
```

`nexo-vending` no auto-crea `Product` desde barcode ni desde descripción manual (ADR-030 se mantiene).

---

# 2. Regla arquitectónica principal

Una reposición física puede ocurrir aunque el catálogo no conozca el producto.

El ledger de inventario **no** puede registrar un movimiento sin `product_id`.

Por lo tanto:

```text
                    CAMPO (móvil / reponedor)
              ┌─────────────────────────────┐
              │ slot                        │
              │ quantity                    │
              │ barcode? / no-scan          │
              │ manual_description (pista)  │
              └──────────────┬──────────────┘
                             │
                             ▼
                    LÍNEA DE REPOSICIÓN
              ┌─────────────────────────────┐
              │ RESOLVED                    │
              │   → product_id known        │
              │ PENDING_PRODUCT_RESOLUTION  │
              │   → product_id = null       │
              │   → manual_description req. │
              └──────────────┬──────────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
     Complete (known)              Admin resolve
              │                             │
              ▼                             ▼
     InventoryMovement             Deferred InventoryMovement
     (product_id required)         (product_id required)
```

La dependencia debe permanecer:

```text
nexo-vending → nexo-platform
```

Nunca:

```text
nexo-platform → nexo-vending
```

---

# 3. Gap actual (punto de partida)

Hoy coexisten tres verdades contradictorias:

### PRD / commit2 / PRODUCT_CATALOG

```text
product_id = NULL
manual_description = "Bebida energética X"
# admin resolves later
```

### HTTP schema / OpenAPI

`AddReplenishmentLineRequest` acepta `product_id` opcional y `manual_description` opcional.

### Dominio / persistencia / complete

* `ReplenishmentLine.product_id: ProductId` (requerido).
* `replenishment_lines.product_id` NOT NULL.
* `AddReplenishmentLine` lanza si `product_id is None`.
* `CompleteReplenishment` copia `line.product_id` a cada `InventoryMovement`.
* `InventoryMovement.product_id` siempre requerido.

V11 elimina la contradicción implementando el modelo pendiente + resolución diferida.

---

# 4. Qué NO hace V11

* No implementa el cliente Flutter (V12+).
* No auto-crea `Product` desde barcode o descripción.
* No escribe `InventoryMovement` con `product_id` null.
* No crea productos placeholder / “UNKNOWN_SKU”.
* No implementa UI admin web completa (solo API + casos de uso).
* No introduce un agregado `Incident` genérico desacoplado de la línea.
* No cambia geofencing ni offline sync.
* No modifica NexoPlatform.

---

# 5. Casos de negocio cubiertos

### A. Producto no catalogado

```text
scan barcode
  → GET /products/barcode/{code} → 404
  → retry
  → 404
  → operador ingresa manual_description
  → POST line (product_id null, PENDING)
```

### B. Código de barras ilegible / no escaneable

```text
embalaje dañado / glare / sin código legible
  → operador no envía barcode (o envía intento fallido)
  → ingresa manual_description
  → POST line (product_id null, PENDING)
```

Ambos casos usan el **mismo mecanismo de dominio**. La diferencia es operativa (pista para el revisor).

---

# 6. Modelo de resolución de línea

Extender el dominio de reposición:

```text
nexo_vending/domain/replenishment/
├── entities.py          # ReplenishmentLine.product_id opcional + status
├── enums.py             # LineResolutionStatus
├── errors.py            # si aplica
└── policies.py          # invariantes de resolución
```

### LineResolutionStatus

```python
class LineResolutionStatus(Enum):
    RESOLVED = "resolved"
    PENDING_PRODUCT_RESOLUTION = "pending_product_resolution"
```

Semántica:

### RESOLVED

La línea tiene `product_id` de catálogo. Puede generar movimientos de inventario (en complete o, si se resolvió después, en resolve).

### PENDING_PRODUCT_RESOLUTION

La línea registra lo ocurrido en campo sin identidad de producto. **No** genera movimientos hasta resolución admin.

---

# 7. ReplenishmentLine (modelo objetivo)

```python
ReplenishmentLine(
    id: ReplenishmentLineId,
    machine_position_id: SlotId,
    product_id: ProductId | None,
    quantity: SignedQuantity,
    unit_price: Decimal,
    occurred_at: datetime,
    product_description_snapshot: str,
    resolution_status: LineResolutionStatus,
    preferred_product_id_snapshot: ProductId | None = None,
    replacement_reason: ReplacementReason | None = None,
    barcode_scanned: Barcode | None = None,
    manual_description: str | None = None,
    resolved_at: datetime | None = None,
    resolved_by_operator_id: OperatorId | None = None,
)
```

Reglas de construcción:

```text
RESOLVED
  → product_id IS NOT NULL
  → product_description_snapshot no vacío
  → manual_description opcional (snapshot aid)

PENDING_PRODUCT_RESOLUTION
  → product_id IS NULL
  → manual_description no vacío (pista obligatoria)
  → product_description_snapshot = manual_description.strip()
  → replacement_reason IS NULL
  → preferred_product_id_snapshot puede existir (slot preferred) pero no implica resolución
```

Prohibido:

```text
product_id = NULL AND manual_description vacío/null
product_id = NULL AND resolution_status = RESOLVED
product_id IS NOT NULL AND resolution_status = PENDING_PRODUCT_RESOLUTION
replacement_reason con línea PENDING
```

---

# 8. Invariantes de dominio

El agregado `Replenishment` protege:

```text
1. add_line solo si status = IN_PROGRESS
2. línea RESOLVED requiere ProductId válido (identidad de catálogo)
3. línea PENDING requiere manual_description
4. quantity ≠ 0
5. slot pertenece a la máquina de la visita
6. resolve_line solo desde PENDING → RESOLVED
7. resolve_line no permitido si visita CANCELLED
8. resolve_line sí permitido si visita COMPLETED (movimientos diferidos)
9. una línea RESOLVED no se reabre
```

Método de dominio sugerido:

```python
replenishment.resolve_line_product(
    line_id,
    product_id,
    product_description_snapshot,
    resolved_at,
    resolved_by_operator_id,
)
```

---

# 9. Flujo de campo (móvil)

```text
StartReplenishment
        │
        ▼
Identify slot
        │
        ▼
Scan barcode? ──yes──► GET /products/barcode/{code}
        │                      │
        │                 ┌────┴────┐
        │                 │         │
        │               200        404
        │                 │         │
        │                 ▼         ▼
        │           product_id   retry?
        │                 │         │
        no                │    still unknown
        │                 │         │
        ▼                 ▼         ▼
 manual_description   RESOLVED   PENDING + manual_description
        │                 │         │
        └────────┬────────┴─────────┘
                 ▼
        POST /replenishments/{id}/lines
                 │
                 ▼
        CompleteReplenishment
```

El móvil **captura**; Vending **decide** validez e impacto de inventario.

---

# 10. Application layer

Crear / extender:

```text
nexo_vending/application/replenishment/
├── add_line.py                 # rama PENDING + rama RESOLVED
├── complete.py                 # movimientos solo líneas RESOLVED
├── resolve_line_product.py     # NUEVO
├── list_pending_lines.py       # NUEVO (cola admin)
└── ...
```

---

# 11. AddReplenishmentLine

Comando (conceptual):

```python
AddReplenishmentLineCommand(
    tenant_id,
    replenishment_id,
    slot_id,
    quantity,
    scanned_at,
    product_id: ProductId | None = None,
    barcode: str | None = None,
    manual_description: str | None = None,
    unit_price: Decimal | None = None,
    replacement_reason: ReplacementReason | None = None,
)
```

Resolución:

```text
1. Si product_id presente → validar catálogo tenant-scoped → RESOLVED
2. Else si barcode presente:
     find_by_barcode
       → found → RESOLVED
       → not found + manual_description → PENDING
       → not found + sin manual → DomainError("product not found")
3. Else si solo manual_description → PENDING
4. Else → DomainError("line requires product identity or manual_description")
```

Reglas adicionales:

### RESOLVED (load)

* Validar stock del reponedor para ese `product_id` (comportamiento actual).
* Sustitución / `replacement_reason` permitidos según reglas existentes.

### PENDING

* **No** validar stock del reponedor (no hay SKU).
* **No** aceptar `replacement_reason`.
* `unit_price`: comando o `slot.selling_price`; si ninguno → error (igual que hoy para precio).
* Capacidad de slot: aplicar las mismas reglas de cantidad/capacidad que ya existan cuando no dependan del producto concreto; si la regla vigente exige preferred product mismatch, documentar que PENDING no evalúa sustitución.

Eliminar el hard-stop actual que rechaza toda línea sin `product_id` **después** de haber aceptado manual description.

---

# 12. CompleteReplenishment (complete parcial de ledger)

Extiende ADR-027 sin romper atomicidad:

```text
CompleteReplenishment (una transacción)
  1. Load replenishment (IN_PROGRESS)
  2. Para cada línea RESOLVED:
       registrar InventoryMovement (idempotent key existente)
  3. Para cada línea PENDING:
       NO registrar movimiento
  4. Marcar visita COMPLETED
  5. Commit (Platform UoW)
```

Consecuencias:

* Visita puede quedar `COMPLETED` con líneas `PENDING_PRODUCT_RESOLUTION`.
* Stock de máquina por SKU puede quedar incompleto hasta resolución (estado honesto).
* Re-complete de visita ya `COMPLETED` sigue siendo no-op.
* Rollback: visita sigue `IN_PROGRESS` y no hay movimientos parciales.

Idempotency key de movimiento (resolved en complete) se mantiene:

```text
{visit_idempotency_key}:line:{line_id}
```

---

# 13. ResolveReplenishmentLineProduct

Nuevo caso de uso admin:

```python
ResolveReplenishmentLineProductCommand(
    tenant_id,
    replenishment_id,
    line_id,
    product_id,
    resolved_at,
    actor_operator_id,
)
```

Flujo:

```text
1. Autorizar actor ADMIN (política Vending)
2. Load replenishment tenant-scoped
3. Line must be PENDING_PRODUCT_RESOLUTION
4. Product must exist in tenant catalog
5. Domain: resolve_line_product(...)
6. Si visita COMPLETED (o se decide post-movimientos siempre al resolve):
     a. Validar stock reponedor si quantity.is_load
     b. Escribir InventoryMovement diferidos (REPLENISHMENT / SLOT_REMOVAL según signo)
     c. Idempotency key: {visit_idempotency_key}:line:{line_id}:resolve
7. Save + commit en una sola transacción
```

Reglas:

* **No** crea Product.
* Si el producto no existe → `DomainError("product not found")` (admin debe crearlo antes vía catálogo).
* Si stock insuficiente en resolución de load → `InsufficientStockError` (sin dejar línea a medias: rollback).
* Segunda resolución de la misma línea → no-op idempotente o error de conflicto explícito; preferir **idempotente** si `product_id` coincide, **conflicto** si intenta otro `product_id`.
* Tenant isolation: no resolver líneas de otro tenant.

---

# 14. ListPendingProductResolutions

Cola de revisión:

```python
ListPendingProductResolutionsQuery(
    tenant_id,
    machine_id: MachineId | None = None,
    replenishment_id: ReplenishmentId | None = None,
)
```

Retorna líneas `PENDING_PRODUCT_RESOLUTION` con contexto mínimo:

```text
replenishment_id
line_id
machine_id
slot_id
quantity
manual_description
barcode_scanned
occurred_at
product_description_snapshot
visit_status
```

---

# 15. Ports

Extender / usar:

```text
ReplenishmentRepository
ProductRepository / ProductLookup
InventoryRepository (expected_quantity + record movement)
UnitOfWork (Platform)
```

No crear un segundo sistema de outbox ni UoW paralelo.

Si se publica evento de negocio al resolver:

```text
ReplenishmentLineProductResolved
```

usar Outbox de Platform dentro de la misma transacción (opcional en V11; si no se publica, documentarlo como Future).

---

# 16. Persistencia

Migración Alembic (nueva revisión después de la cadena vigente):

```text
replenishment_lines.product_id          NULLABLE
replenishment_lines.resolution_status   NOT NULL
                                        DEFAULT 'resolved' para filas existentes
replenishment_lines.resolved_at         NULLABLE
replenishment_lines.resolved_by_operator_id NULLABLE
```

Constraints:

```sql
CHECK (
  (
    resolution_status = 'resolved'
    AND product_id IS NOT NULL
  )
  OR
  (
    resolution_status = 'pending_product_resolution'
    AND product_id IS NULL
    AND manual_description IS NOT NULL
    AND length(trim(manual_description)) > 0
  )
)
```

Índice sugerido:

```text
(tenant vía join/visit, resolution_status)
o índice en replenishment_lines(resolution_status) + lookup por replenishment_id
```

`inventory_movements.product_id` permanece NOT NULL.

ORM + mappers deben preservar `None` solo en PENDING.

Backfill:

```text
todas las líneas existentes → resolution_status = resolved
```

---

# 17. API HTTP

### Campo / reponedor (existente, contrato corregido)

`POST /replenishments/{id}/lines`

Body permitido (PENDING):

```json
{
  "slot_id": "...",
  "quantity": 5,
  "barcode": "123456789",
  "manual_description": "Bebida energética X",
  "product_id": null
}
```

Body permitido (RESOLVED):

```json
{
  "slot_id": "...",
  "product_id": "...",
  "quantity": 5
}
```

Body inválido:

```json
{
  "slot_id": "...",
  "quantity": 5,
  "product_id": null,
  "manual_description": null
}
```

`ReplenishmentLineOut`:

* `product_id`: string | null
* `resolution_status`: `resolved` | `pending_product_resolution`
* `manual_description`: string | null
* `resolved_at`, `resolved_by_operator_id` cuando aplique

### Admin

```text
GET  /replenishments/pending-product-resolutions
POST /replenishments/{id}/lines/{line_id}/resolve-product
```

Resolve body:

```json
{
  "product_id": "..."
}
```

Permisos:

* add-line / complete: operador autorizado a reponer (existente).
* list pending / resolve: rol ADMIN Vending (o permiso explícito `replenishment.resolve_product`).

Actualizar:

* `docs/api/openapi-v1.json` (vía export)
* `docs/api/REPLENISHMENT_API.md`
* `docs/api/REPLENISHMENT_EXECUTION_API.md`
* `docs/api/MOBILE_API_CONTRACT.md`

---

# 18. Mobile contract (V11)

Tras barcode 404 o sin scan legible:

```text
1. Reintentar scan (UX)
2. Si sigue desconocido / ilegible:
   capturar manual_description (obligatorio)
   POST line sin product_id
3. Continuar reposición
4. Complete permitido con pendientes
5. Mostrar en UI local que hay ítems “pendientes de catálogo” (opcional UX)
```

Prohibido en móvil:

* inventar `product_id`
* crear producto
* asumir que el stock de máquina por SKU ya refleja la línea PENDING

---

# 19. Precio, stock, auditoría, regularización

| Concern | PENDING (campo) | Tras resolve admin |
| --- | --- | --- |
| Inventario máquina | sin movimiento | `InventoryMovement` diferido |
| Stock reponedor | sin validar / sin debitar | validar + debitar si load |
| Precio línea | slot/comando | se mantiene; no recalcula catálogo salvo política futura |
| Producto | null | `product_id` de catálogo existente |
| Auditoría | línea + manual_description + barcode? + actor visita | + resolved_at + resolved_by |
| Regularización | cola admin | resolve-product |

La pista (`manual_description`) **no** es el producto; es evidencia para el revisor.

---

# 20. Relación con ADRs existentes

* **ADR-004 / ADR-018** — Replenishment como agregado: se mantiene; resolve es comportamiento del agregado.
* **ADR-017 / ADR-003** — Ledger por producto: se mantiene; nunca movimiento sin producto.
* **ADR-027** — Complete transaccional: se especializa a “movimientos de líneas RESOLVED”; resolve usa su propia transacción atómica.
* **ADR-030** — No auto-create desde barcode: se mantiene.
* **ADR-019** — Sustitución: no aplica a PENDING.
* **ADR-022** — Snack sale sin product: precedente de “atribuación diferida/honesta”, pero **no** se reutiliza para inventario de reposición.

---

# 21. Tests de dominio — LineResolutionStatus e invariantes

```text
test_resolved_line_requires_product_id
test_pending_line_requires_manual_description
test_pending_line_rejects_empty_manual_description
test_pending_line_rejects_replacement_reason
test_cannot_construct_resolved_without_product
test_cannot_construct_pending_with_product_id
```

---

# 22. Tests de AddReplenishmentLine

```text
test_add_resolved_line_by_product_id
test_add_resolved_line_by_barcode_lookup
test_add_pending_line_when_barcode_unknown_with_manual_description
test_add_pending_line_without_barcode_with_manual_description
test_reject_unknown_barcode_without_manual_description
test_reject_line_without_product_and_without_manual_description
test_pending_line_skips_replenisher_stock_check
test_resolved_load_still_checks_replenisher_stock
test_pending_line_uses_slot_selling_price_when_unit_price_omitted
```

---

# 23. Tests de CompleteReplenishment con líneas mixtas

```text
test_complete_writes_movements_only_for_resolved_lines
test_complete_allowed_with_pending_lines
test_complete_leaves_pending_lines_unresolved
test_complete_rollback_leaves_no_movements
test_recomplete_is_noop
test_movement_idempotency_key_unchanged_for_resolved_lines
```

---

# 24. Tests de ResolveReplenishmentLineProduct

```text
test_resolve_assigns_product_and_marks_resolved
test_resolve_writes_deferred_inventory_movements_when_visit_completed
test_resolve_validates_replenisher_stock_on_load
test_resolve_insufficient_stock_rolls_back_line_state
test_resolve_rejects_unknown_product
test_resolve_does_not_auto_create_product
test_resolve_idempotent_same_product
test_resolve_conflict_different_product
test_resolve_rejected_for_cancelled_visit
test_resolve_allowed_on_completed_visit
test_resolve_not_allowed_twice_after_resolved
```

---

# 25. Tests de tenant isolation

```text
test_cannot_add_pending_line_to_other_tenant_replenishment
test_cannot_list_pending_lines_across_tenants
test_cannot_resolve_line_of_other_tenant
test_cannot_resolve_with_product_from_other_tenant
```

---

# 26. Tests de concurrencia (PostgreSQL / Testcontainers)

```text
test_concurrent_resolve_same_line_one_wins
test_concurrent_complete_and_resolve_do_not_duplicate_movements
test_resolve_idempotency_under_retry
```

Demostrar:

* no lost update de `resolution_status`
* no doble movimiento con la misma idempotency key de resolve

---

# 27. Tests de API

```text
test_post_line_pending_returns_null_product_id_and_pending_status
test_post_line_invalid_without_product_or_manual_returns_4xx
test_get_pending_product_resolutions_admin_ok
test_get_pending_product_resolutions_operator_forbidden
test_post_resolve_product_admin_ok
test_post_resolve_product_operator_forbidden
test_barcode_404_then_pending_line_e2e_api_flow
```

---

# 28. Tests de arquitectura

```text
test_domain_replenishment_does_not_import_fastapi
test_domain_replenishment_does_not_import_sqlalchemy
test_no_inventory_movement_without_product_id_in_domain
test_dependency_direction_vending_to_platform_only
```

---

# 29. Application tests adicionales

```text
test_list_pending_filters_by_machine
test_list_pending_excludes_resolved
test_complete_then_resolve_produces_single_deferred_movement
test_in_progress_resolve_updates_line_before_complete_then_complete_writes_movement_once
```

Nota sobre resolve mientras `IN_PROGRESS`:

* Permitido: la línea pasa a RESOLVED antes del complete.
* Complete posterior escribe el movimiento con la key estándar `:line:{line_id}` (no `:resolve`).
* Documentar en implementación la regla exacta para evitar doble escritura:

```text
si resolve ocurre antes de COMPLETED → no escribir movimiento en resolve;
si resolve ocurre después de COMPLETED → escribir movimiento diferido con :resolve
```

---

# 30. No Flutter todavía

V11 deja el backend listo para Flutter:

```text
Flutter (V12+)
     │
     ▼
HTTP API V11
     │
     ▼
Application / Domain
```

No agregar proyecto móvil en este commit.

---

# 31. Documentación

Agregar / actualizar:

```text
docs/
├── commits/
│   ├── commit11.md              # este documento
│   └── secuencia.md             # V11 = unresolved product
├── adr/
│   └── ADR-032-deferred-product-resolution-on-replenishment.md
├── architecture/
│   └── PRODUCT_CATALOG.md       # flujo unknown → PENDING, no auto-create
├── domain/
│   └── REPLENISHMENT_RULES.md   # invariantes PENDING/RESOLVED (si existe; si no, crear sección)
├── api/
│   ├── MOBILE_API_CONTRACT.md
│   ├── REPLENISHMENT_API.md
│   ├── REPLENISHMENT_EXECUTION_API.md
│   └── openapi-v1.json
└── (prd.md nota Implemented vs Planned alineada)
```

---

# 32. ADR-032 — Deferred product resolution on replenishment

**Context**

En campo, un reponedor puede cargar un producto no catalogado o con barcode ilegible. El negocio necesita registrar cantidad/slot/pista, pero el ledger exige `product_id`.

**Decision**

1. Permitir `ReplenishmentLine` en estado `PENDING_PRODUCT_RESOLUTION` con `product_id = null` y `manual_description` obligatoria.
2. `CompleteReplenishment` solo genera movimientos para líneas `RESOLVED`.
3. Admin resuelve con `ResolveReplenishmentLineProduct` usando un `Product` ya existente.
4. Los movimientos diferidos ocurren en la transacción de resolución si la visita ya está `COMPLETED`.
5. No auto-crear productos.

**Consequences**

* Stock por SKU puede retrasarse respecto de la realidad física hasta la revisión.
* Auditoría de campo permanece en la línea pendiente.
* Se elimina la contradicción PRD ↔ API ↔ dominio.

**Alternatives considered**

1. Bloquear reposición sin producto (opción A pura) — rechazada para V11; no cubre la operación real.
2. Auto-crear Product desde manual_description — rechazada (ADR-030 / catálogo controlado).
3. InventoryMovement sin product_id — rechazada; rompe el ledger.
4. Incident genérico sin línea de reposición — rechazada; pierde vínculo con visita/slot/cantidad.

---

# 33. PRODUCT_CATALOG.md (actualización)

Reemplazar la flecha ambigua:

```text
Unknown barcode → Replenishment manual_description
```

por:

```text
Unknown / unreadable barcode
        ↓
ReplenishmentLine PENDING_PRODUCT_RESOLUTION
  (manual_description required, product_id null)
        ↓
Admin creates Product in catalog (separate use case)
        ↓
ResolveReplenishmentLineProduct
        ↓
Deferred InventoryMovement
```

---

# 34. MOBILE_API_CONTRACT.md (actualización)

Documentar explícitamente:

* barcode 404 → camino PENDING permitido.
* `manual_description` obligatorio en ese camino.
* `product_id` null permitido en response de línea pendiente.
* complete con pendientes permitido.
* checklist: no auto-create; sí pending line.

Eliminar el hedge actual “only if the backend contract allows it / line still needs resolved product_id” sustituyéndolo por el contrato V11.

---

# 35. Criterios de aceptación

El Commit 11 sólo se considera aprobado si:

## Domain

* [ ] existe `LineResolutionStatus`.
* [ ] línea PENDING exige `manual_description` y `product_id is None`.
* [ ] línea RESOLVED exige `product_id`.
* [ ] PENDING rechaza `replacement_reason`.
* [ ] resolve solo PENDING → RESOLVED.
* [ ] línea RESOLVED no se reabre.

## Add line

* [ ] barcode desconocido + manual → PENDING.
* [ ] sin barcode + manual → PENDING.
* [ ] barcode desconocido sin manual → error.
* [ ] sin product y sin manual → error.
* [ ] PENDING no chequea stock reponedor.
* [ ] RESOLVED load sí chequea stock reponedor.

## Complete

* [ ] complete permitido con líneas PENDING.
* [ ] movimientos solo para RESOLVED.
* [ ] rollback no deja movimientos parciales.
* [ ] re-complete no duplica movimientos.

## Resolve

* [ ] admin asigna `product_id` existente.
* [ ] no auto-crea Product.
* [ ] si visita COMPLETED → movimiento diferido atómico.
* [ ] stock insuficiente en resolve → rollback total.
* [ ] idempotencia de resolve bajo retry.
* [ ] conflicto si se intenta otro producto.

## Inventory

* [ ] ningún `InventoryMovement` sin `product_id`.
* [ ] keys de idempotencia no colisionan entre complete y resolve.

## API

* [ ] OpenAPI refleja `product_id` nullable + `resolution_status`.
* [ ] endpoints list pending + resolve-product.
* [ ] autorización admin en resolve/list.
* [ ] mobile contract alineado.

## Tenant isolation

* [ ] no list/resolve cross-tenant.
* [ ] no resolve con product de otro tenant.

## Architecture

* [ ] dominio sin FastAPI/SQLAlchemy.
* [ ] no se modificó NexoPlatform.
* [ ] no se duplicó UoW/Outbox.
* [ ] dirección Vending → Platform.

## Tests

* [ ] unit domain.
* [ ] application add/complete/resolve/list.
* [ ] API tests.
* [ ] PostgreSQL concurrency/rollback donde aplica.
* [ ] architecture tests.
* [ ] regresión V0–V10 relevante en verde.

## Quality

* [ ] `pytest` pasa.
* [ ] `ruff check` pasa.
* [ ] migraciones Alembic aplican en limpio.
* [ ] Docker smoke / Testcontainers baseline OK.
* [ ] sin secretos ni TODOs críticos que oculten el gap.

## Documentation

* [ ] ADR-032 creado.
* [ ] PRODUCT_CATALOG / REPLENISHMENT / MOBILE / OpenAPI actualizados.
* [ ] PRD/docs distinguen Implemented vs Planned.
* [ ] `secuencia.md` apunta V11 a este commit.

---

# 36. Definition of Done

El commit queda cerrado cuando la siguiente cadena funciona:

```text
Field operator
   ↓
barcode unknown OR unreadable
   ↓
AddReplenishmentLine (PENDING + manual_description)
   ↓
CompleteReplenishment
   ├── RESOLVED lines → InventoryMovement
   └── PENDING lines → no movement
   ↓
Admin creates Product in catalog (if needed)
   ↓
ResolveReplenishmentLineProduct
   ↓
Deferred InventoryMovement (same transaction as resolve)
   ↓
Line RESOLVED + audit trail intact
```

Y queda explícitamente prohibida esta cadena:

```text
Unknown barcode
   ↓
auto-create Product
   ↓
silent inventory with invented SKU
```

---

# 37. Fuera de alcance (recordatorio)

| Tema | Dónde |
| --- | --- |
| Flutter client | V12+ |
| Offline & sync | V13+ |
| Admin Web UI | V14+ |
| Alerts & audit dashboards | V15+ |
| Production hardening | V16+ |
| Auto-create product | Nunca en este flujo |
| Geofencing | No en V11 |

---

# 38. Resultado final de V11

Al cerrar V11:

1. El PRD y la API dejan de contradecir al dominio: PENDING es un estado de primera clase.
2. El reponedor puede registrar cantidad + pista cuando el producto no está en catálogo o el barcode no se lee.
3. El ledger permanece íntegro: ningún movimiento sin `product_id`.
4. Admin puede regularizar después sin rehacer la visita.
5. Flutter (V12) consume un contrato estable para el camino 404 → manual → pending line.
6. La documentación (ADR-032 + contratos) describe lo **implementado**, no un flujo fantasma.

```text
V10 execution context
        ↓
V11 unresolved product + deferred inventory
        ↓
V12 Flutter mobile (consume V11)
```
