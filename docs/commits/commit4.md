# Commit V4 — Product Catalog

**Commit message**

`feat(vending): establish tenant-scoped product catalog`

## 1. Objetivo

Implementar el **Product Catalog** de `nexo-vending`, estableciendo el modelo de productos y sus reglas de negocio antes de introducir persistencia y APIs.

El catálogo debe:

* ser tenant-scoped;
* soportar identificación mediante código de barras;
* permitir búsqueda por barcode;
* mantener información descriptiva del producto;
* controlar productos activos/inactivos;
* definir umbrales de bajo stock;
* evitar duplicación de productos dentro del tenant;
* permitir productos desconocidos durante una reposición sin crear automáticamente un producto maestro.

La autenticación, identidad, tenant context y demás capacidades transversales deben continuar siendo provistas por:

```text
nexo-platform==1.2.0
```

---

# 2. Frontera arquitectónica

La responsabilidad queda dividida así:

```text
┌──────────────────────────────────────────────┐
│             nexo-platform 1.2.0             │
│                                              │
│ RequestContext                               │
│ Tenant context                               │
│ Principal                                    │
│ Authentication                              │
│ Authorization primitives                    │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                nexo-vending                  │
│                                              │
│ Product                                      │
│ Barcode                                      │
│ Category                                     │
│ ProductStatus                                │
│ Catalog rules                                │
│ Product lookup                               │
│ Tenant-scoped catalog                        │
└──────────────────────────────────────────────┘
```

## Regla

Vending **no debe implementar nuevamente**:

```text
Authentication
Principal
AuthenticatedIdentity
ExternalIdentity
RequestContext
Tenant context
JWT
Google OAuth
```

Vending solamente consume esas capacidades desde Platform cuando sean necesarias en Application/API.

---

# 3. Product Aggregate

El agregado principal será:

```text
Product
```

No introducir todavía un `ProductCatalog` Aggregate Root innecesario.

El catálogo será inicialmente un conjunto de productos tenant-scoped administrados mediante el `Product` como Aggregate Root.

Modelo:

```text
Product
├── id
├── tenant_id
├── barcode
├── name
├── description
├── brand
├── category
├── unit
├── low_stock_threshold
├── status
├── created_at
└── updated_at
```

---

# 4. Tenant

El producto pertenece a un tenant.

Conceptualmente:

```text
Tenant
  │
  └── Product Catalog
         ├── Product A
         ├── Product B
         └── Product C
```

No debe existir un catálogo global accidentalmente compartido entre tenants.

El `tenant_id` se obtiene desde:

```text
nexo-platform RequestContext
```

en Application/API.

El dominio Vending no debe importar directamente `RequestContext`.

La frontera debe ser:

```text
RequestContext
      │
      ▼
Application
      │
      ▼
tenant_id
      │
      ▼
Product domain
```

---

# 5. ProductId

Crear:

```python
ProductId
```

como Value Object/identifier propio de Vending.

Debe ser independiente de la base de datos.

Recomendación:

```text
UUID
```

El ID interno no debe ser el barcode.

Por lo tanto:

```text
ProductId ≠ Barcode
```

---

# 6. Barcode

Crear:

```python
Barcode
```

como Value Object.

Responsabilidades:

* no vacío;
* eliminación de espacios externos;
* normalización;
* comparación consistente;
* longitud razonable;
* caracteres válidos.

El barcode no debe utilizarse como ID técnico del agregado.

Ejemplo:

```text
" 7801234567890 "
```

debe normalizarse antes de ser almacenado/buscado.

La normalización exacta debe quedar encapsulada en `Barcode`, no repartida entre API, repositorio y casos de uso.

---

# 7. Barcode y tipos de códigos

V4 no debe asumir que todos los productos utilizan exclusivamente EAN-13.

El Value Object debe permitir códigos de barra reales utilizados por vending, pero sin introducir todavía una jerarquía innecesaria de:

```text
EAN13
EAN8
UPC
Code128
...
```

La validación debe ser pragmática.

La responsabilidad de V4 es:

```text
identificador escaneable válido
```

no construir todavía un motor universal de estándares de barcode.

---

# 8. ProductName

Crear:

```python
ProductName
```

o mantener el nombre como string validado según la convención utilizada en V1/V3.

Debe garantizar:

* no vacío;
* trim;
* longitud máxima razonable.

No permitir:

```text
""
"   "
```

---

# 9. ProductDescription

La descripción puede ser opcional.

```text
description: str | None
```

Pero si existe:

* no debe ser whitespace-only;
* debe normalizarse.

Esto es importante porque V4 debe soportar posteriormente el caso:

```text
barcode encontrado
      ↓
Product
      ↓
description
```

---

# 10. Brand

Crear:

```text
brand: str | None
```

No hacer `Brand` un agregado separado.

Por ahora es metadata del producto.

Más adelante podría evolucionar si aparecen reglas propias de marca.

---

# 11. Category

Crear una categoría de catálogo.

Para V4 recomiendo que inicialmente sea un Value Object/string normalizado y **no un agregado persistente independiente**.

Ejemplos:

```text
Bebidas
Snacks
Chocolates
Galletas
Barras
Otros
```

No hardcodear todavía un enum cerrado si el administrador necesitará crear categorías.

La entidad `ProductCategory` independiente puede introducirse cuando exista una necesidad real de administración del catálogo.

---

# 12. Unit

Crear:

```python
ProductUnit
```

con valores iniciales:

```text
UNIT
PACKAGE
BOTTLE
CAN
```

o, si el modelo V1 ya estableció una enumeración diferente, reutilizar esa convención.

El objetivo es evitar cantidades ambiguas.

Por ejemplo:

```text
quantity = 5
unit = UNIT
```

es diferente conceptualmente de:

```text
quantity = 5
unit = PACKAGE
```

---

# 13. Low Stock Threshold

El producto tendrá:

```text
low_stock_threshold
```

Este valor **no representa stock actual**.

Representa solamente:

> cantidad mínima a partir de la cual el sistema considera que el producto requiere atención.

Ejemplo:

```text
Product:
    low_stock_threshold = 10

Inventory:
    stock = 7
```

La condición de low stock se determinará posteriormente en Inventory.

V4 solamente define el dato de catálogo.

---

# 14. ProductStatus

Definir:

```python
class ProductStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
```

Un producto inactivo:

* no puede utilizarse en nuevas operaciones normales;
* permanece en el historial;
* no se elimina físicamente.

Esto es importante para preservar:

```text
Replenishment history
Inventory history
Audit history
```

---

# 15. Soft delete

No implementar:

```text
DELETE Product
```

como eliminación física de negocio.

La desactivación será:

```text
ACTIVE → INACTIVE
```

El producto histórico debe continuar existiendo.

Esto permitirá que una reposición antigua siga mostrando:

```text
Product ID
Product description snapshot
Barcode
```

aunque el producto posteriormente haya sido desactivado.

---

# 16. Product invariants

El agregado debe garantizar:

### Barcode

```text
barcode != empty
```

### Name

```text
name != empty
```

### Low stock threshold

```text
threshold >= 0
```

### Tenant

```text
tenant_id != null
```

### Status

Siempre debe existir un estado válido.

### Immutable identity

Una vez creado el producto:

```text
ProductId
tenant_id
```

no deben cambiar.

---

# 17. Barcode uniqueness

La regla de negocio será:

> Un barcode identifica como máximo un producto activo dentro de un tenant.

Conceptualmente:

```text
Tenant A
7801234567890 → Product X

Tenant B
7801234567890 → Product Y
```

es válido.

Pero:

```text
Tenant A
7801234567890 → Product X
7801234567890 → Product Y
```

no es válido.

Importante:

La unicidad definitiva deberá reforzarse posteriormente mediante PostgreSQL.

V4 debe establecer el contrato:

```text
find_by_barcode(tenant_id, barcode)
```

y V5 deberá convertirlo en una constraint real.

---

# 18. ProductRepository

Crear el port:

```python
ProductRepository
```

con operaciones conceptuales:

```python
get(product_id)

save(product)

find_by_barcode(
    tenant_id,
    barcode,
)

list_active(
    tenant_id,
)
```

No implementar PostgreSQL en V4.

---

# 19. ProductCatalog service

Crear un servicio/port para búsqueda:

```text
ProductLookup
```

Contrato:

```python
find_by_barcode(
    tenant_id,
    barcode,
) -> Product | None
```

Este contrato será utilizado posteriormente por:

```text
Replenishment
```

cuando el operador escanee un producto.

---

# 20. Unknown barcode

Este punto es fundamental para el flujo móvil.

Cuando el operador escanea:

```text
7801234567890
```

y no existe:

```text
ProductLookup
       ↓
None
```

V4 **no crea automáticamente un Product**.

La aplicación posteriormente podrá permitir:

```text
Primer scan
    ↓
Producto no encontrado
    ↓
Segundo scan
    ↓
Producto no encontrado
    ↓
manual_description
```

Esto pertenece al flujo de Replenishment, no al catálogo.

Por tanto:

```text
Unknown barcode
      ≠
Create Product
```

---

# 21. Product description snapshot

V4 debe documentar explícitamente una relación con el futuro Replenishment.

Cuando una reposición utilice un producto conocido, la línea de reposición deberá conservar:

```text
product_id
barcode_scanned
product_description_snapshot
```

El snapshot evita que:

```text
Product
   ↓
renamed later
```

modifique históricamente una reposición anterior.

V4 no implementa todavía ese snapshot; solamente establece el contrato que V7 deberá respetar.

---

# 22. Application use cases

Crear:

```text
nexo_vending/application/products/
├── create_product.py
├── update_product.py
├── activate_product.py
├── deactivate_product.py
└── find_product_by_barcode.py
```

---

# 23. CreateProduct

Entrada conceptual:

```text
tenant_id
barcode
name
description
brand
category
unit
low_stock_threshold
```

El tenant debe venir del contexto autenticado, no del cliente.

Flujo:

```text
RequestContext
      ↓
tenant_id
      ↓
CreateProduct
      ↓
ProductRepository.find_by_barcode()
      ↓
no duplicate
      ↓
Product.create()
      ↓
save()
```

---

# 24. UpdateProduct

Debe permitir modificar datos descriptivos:

```text
name
description
brand
category
unit
low_stock_threshold
```

No permitir modificar:

```text
product_id
tenant_id
```

El barcode merece tratamiento especial.

Recomiendo que V4 permita cambiarlo únicamente mediante una operación explícita:

```text
ChangeProductBarcode
```

y no como parte de un `update_product()` genérico.

Esto evita modificar accidentalmente la identidad comercial utilizada por scanners.

---

# 25. ActivateProduct

```text
INACTIVE → ACTIVE
```

Debe ser explícito.

No debe modificar:

```text
created_at
product_id
tenant_id
```

---

# 26. DeactivateProduct

```text
ACTIVE → INACTIVE
```

Debe ser idempotente o devolver un error de estado según la convención de dominio que adoptemos.

Mi recomendación:

```text
deactivate already inactive
```

sea una operación idempotente en Application.

---

# 27. FindProductByBarcode

Este será un caso de uso importante para Mobile.

Entrada:

```text
RequestContext
Barcode
```

Resultado:

```text
Product | None
```

Nunca debe devolver productos de otro tenant.

---

# 28. Tenant isolation en Product Catalog

El caso crítico:

```text
Tenant A
Barcode X → Product A

Tenant B
Barcode X → Product B
```

es válido.

Pero:

```text
Tenant A request
find_by_barcode(X)
```

debe devolver exclusivamente:

```text
Product A
```

Nunca:

```text
Product B
```

El repository contract debe reflejarlo explícitamente:

```python
find_by_barcode(tenant_id, barcode)
```

y no:

```python
find_by_barcode(barcode)
```

---

# 29. Tests de Barcode

Crear:

```text
tests/unit/domain/products/test_barcode.py
```

Tests:

```text
test_barcode_rejects_empty
test_barcode_rejects_whitespace
test_barcode_trims_whitespace
test_barcode_normalizes_value
test_barcode_equality
test_barcode_inequality
```

Agregar casos representativos de códigos utilizados por el negocio.

---

# 30. Tests de Product

```text
tests/unit/domain/products/test_product.py
```

Tests:

```text
test_product_requires_tenant
test_product_requires_barcode
test_product_requires_name
test_product_accepts_optional_description
test_product_accepts_optional_brand
test_product_accepts_category
test_product_requires_valid_unit
test_product_accepts_zero_threshold
test_product_rejects_negative_threshold
test_product_starts_active
```

---

# 31. Tests de lifecycle

```text
test_active_product_can_be_deactivated
test_inactive_product_can_be_activated
test_product_id_cannot_change
test_tenant_id_cannot_change
test_deactivated_product_remains_identifiable
```

---

# 32. Tests de barcode uniqueness

Con fake repository:

```text
test_same_barcode_is_rejected_within_tenant
test_same_barcode_is_allowed_in_different_tenant
test_inactive_product_does_not_create_duplicate_active_barcode
```

El último caso deberá quedar alineado con la regla elegida para reutilización de barcode.

Recomendación para V4:

> Un barcode no puede estar asociado simultáneamente a dos productos del mismo tenant, aunque uno esté inactivo.

Así evitamos ambigüedad histórica y simplificamos el lookup.

---

# 33. Tests de Application

Crear:

```text
tests/application/products/
```

### Create

```text
test_create_product
test_create_product_rejects_duplicate_barcode
test_create_product_uses_context_tenant
```

### Update

```text
test_update_product
test_update_product_preserves_identity
test_update_product_rejects_cross_tenant_product
```

### Activate

```text
test_activate_product
```

### Deactivate

```text
test_deactivate_product
```

### Lookup

```text
test_find_product_by_barcode
test_find_product_by_barcode_returns_none
test_find_product_by_barcode_is_tenant_scoped
```

---

# 34. Security / authorization tests

El catálogo no debe confiar en:

```text
tenant_id
actor_id
```

enviado por el cliente.

Tests:

```text
test_create_product_uses_authenticated_tenant
test_update_product_cannot_cross_tenant
test_deactivate_product_cannot_cross_tenant
test_lookup_cannot_cross_tenant
```

La autorización de quién puede administrar catálogo utilizará la identidad resuelta en V3:

```text
Platform Principal
        ↓
Vending Operator
        ↓
Role
        ↓
Catalog authorization
```

No crear un sistema de autenticación adicional.

---

# 35. Platform integration tests

Agregar tests que utilicen el `RequestContext` real de:

```text
nexo-platform==1.2.0
```

y comprueben:

```text
context.tenant_id
context.principal
```

son consumidos por la Application Layer.

El test debe demostrar:

```text
Platform RequestContext
        ↓
Vending CreateProduct
        ↓
Product.tenant_id
```

No:

```text
HTTP payload.tenant_id
        ↓
Product
```

---

# 36. Architecture tests

Extender las reglas arquitectónicas existentes.

## Domain

No puede importar:

```text
FastAPI
SQLAlchemy
Alembic
PostgreSQL
nexo-platform
```

El dominio de Product Catalog debe permanecer independiente.

## Application

Puede importar:

```text
domain
platform contracts/context
```

cuando sean necesarios para la frontera de aplicación.

No puede importar:

```text
infrastructure implementations
```

## Infrastructure

Puede implementar:

```text
ProductRepository
```

en futuros commits.

---

# 37. Platform dependency test

Debe existir una prueba que garantice que Vending continúa usando la versión requerida:

```text
nexo-platform==1.2.0
```

y que los objetos de Platform utilizados provienen realmente del paquete instalado.

No copiar:

```text
RequestContext
Principal
Tenant
```

a `nexo-vending`.

---

# 38. No migration

V4 no crea:

```text
0002_products.py
```

ni modifica la migración V0.

El modelo de persistencia llegará posteriormente.

Esto permite primero validar:

```text
Domain
Application
Contracts
Invariants
```

antes de congelar el esquema PostgreSQL.

---

# 39. Documentación

Agregar:

```text
docs/
├── architecture/
│   └── PRODUCT_CATALOG.md
├── adr/
│   ├── ADR-008-product-as-aggregate-root.md
│   ├── ADR-009-barcode-identity.md
│   └── ADR-010-product-history.md
└── domain/
    └── PRODUCT_CATALOG_RULES.md
```

---

# 40. PRODUCT_CATALOG.md

Documentar:

```text
Tenant
  │
  └── Product Catalog
       │
       ├── Product
       │    ├── Barcode
       │    ├── Name
       │    ├── Description
       │    ├── Brand
       │    ├── Category
       │    ├── Unit
       │    ├── Low Stock Threshold
       │    └── Status
       │
       └── Product Lookup
```

También documentar el flujo:

```text
Barcode scan
     ↓
FindProductByBarcode
     ↓
Product found?
   ┌─┴─┐
  yes  no
   │    │
   ▼    ▼
Product  Unknown barcode
          │
          ▼
     Replenishment flow
```

---

# 41. ADR-008 — Product as Aggregate Root

Decisión:

`Product` es Aggregate Root.

No crear un `ProductCatalog` Aggregate Root mientras no exista una regla que requiera coordinación transaccional entre múltiples productos.

Esto mantiene el modelo simple.

---

# 42. ADR-009 — Barcode Identity

Decisión:

El barcode es un identificador comercial externo, no el identificador técnico del agregado.

```text
ProductId ≠ Barcode
```

La unicidad es:

```text
tenant_id + barcode
```

---

# 43. ADR-010 — Product History

Decisión:

Los productos no se eliminan físicamente como operación de negocio.

Se desactivan.

Esto permite conservar referencias históricas desde:

```text
Replenishment
InventoryMovement
AuditEvent
```

---

# 44. PRODUCT_CATALOG_RULES.md

Debe contener explícitamente:

### Creation

```text
tenant required
barcode required
name required
threshold >= 0
```

### Identification

```text
ProductId = internal identity
Barcode = external/commercial identity
```

### Lifecycle

```text
ACTIVE ↔ INACTIVE
```

### Tenant

```text
barcode uniqueness = tenant scoped
```

### Unknown barcode

```text
unknown barcode does not create Product automatically
```

### History

```text
inactive != deleted
```

---

# 45. Criterios de aceptación

El Commit V4 se considera aprobado solamente si:

## Product domain

* [ ] existe `Product`;
* [ ] existe `ProductId`;
* [ ] existe `Barcode`;
* [ ] existe `ProductStatus`;
* [ ] existe `ProductUnit`;
* [ ] existe `low_stock_threshold`;
* [ ] Product es Aggregate Root;
* [ ] Product pertenece a un tenant.

## Barcode

* [ ] barcode no puede estar vacío;
* [ ] barcode se normaliza;
* [ ] barcode no es ProductId;
* [ ] barcode es único dentro del tenant;
* [ ] el mismo barcode puede existir en tenants distintos;
* [ ] lookup siempre es tenant-scoped.

## Lifecycle

* [ ] producto comienza ACTIVE;
* [ ] producto puede desactivarse;
* [ ] producto puede activarse;
* [ ] producto desactivado permanece disponible para historial;
* [ ] no existe hard delete de negocio.

## Catalog

* [ ] se puede crear producto;
* [ ] se puede actualizar metadata;
* [ ] se puede activar/desactivar;
* [ ] se puede buscar por barcode;
* [ ] producto inexistente devuelve `None`;
* [ ] producto desconocido no se crea automáticamente.

## Tenant isolation

* [ ] tenant proviene del contexto de Platform;
* [ ] cliente no puede elegir arbitrariamente el tenant;
* [ ] lookup no puede cruzar tenants;
* [ ] update no puede cruzar tenants;
* [ ] deactivate no puede cruzar tenants.

## Platform

* [ ] Vending consume `nexo-platform==1.2.0`;
* [ ] utiliza `RequestContext` de Platform cuando corresponde;
* [ ] no duplica `Principal`;
* [ ] no duplica `AuthenticatedIdentity`;
* [ ] no duplica `ExternalIdentity`;
* [ ] no implementa autenticación;
* [ ] no implementa OAuth;
* [ ] no implementa JWT.

## Architecture

* [ ] domain no depende de Platform;
* [ ] application puede consumir contratos de Platform en la frontera necesaria;
* [ ] domain no depende de FastAPI;
* [ ] domain no depende de SQLAlchemy;
* [ ] domain no depende de PostgreSQL;
* [ ] application no depende de infrastructure.

## Tests

* [ ] Value Object tests;
* [ ] Product tests;
* [ ] lifecycle tests;
* [ ] barcode uniqueness tests;
* [ ] tenant isolation tests;
* [ ] application tests;
* [ ] Platform integration contract tests;
* [ ] architecture tests;
* [ ] regresión completa de V0–V3.

## Quality

* [ ] Ruff limpio;
* [ ] type checking limpio, si está en baseline;
* [ ] coverage no disminuye respecto del baseline;
* [ ] clean install funciona;
* [ ] Docker smoke continúa funcionando;
* [ ] Testcontainers existente continúa funcionando.

---

# 46. Definition of Done

V4 queda cerrado cuando:

```text
Product Domain
      +
Barcode
      +
Catalog lifecycle
      +
Tenant isolation
      +
Product lookup
      +
Platform RequestContext
      +
Tests
      +
Architecture rules
      +
Documentation
```

están implementados y validados.

No debe existir todavía:

```text
PostgreSQL ProductRepository
Alembic Product migration
REST Product API
Flutter Product UI
Barcode scanner implementation
Inventory stock calculation
Google OAuth
```

---

# 47. Resultado arquitectónico

Al terminar V4:

```text
                  nexo-platform 1.2.0
                         │
                         │ RequestContext
                         │ tenant_id
                         ▼
                  ┌───────────────┐
                  │   Application │
                  └───────┬───────┘
                          │
                          ▼
                  ┌───────────────┐
                  │    Product    │
                  │ Aggregate Root│
                  ├───────────────┤
                  │ ProductId     │
                  │ TenantId      │
                  │ Barcode       │
                  │ Name          │
                  │ Description   │
                  │ Brand         │
                  │ Category      │
                  │ Unit          │
                  │ Threshold     │
                  │ Status        │
                  └───────┬───────┘
                          │
                          ▼
                   ProductLookup
                          │
                 ┌────────┴────────┐
                 ▼                 ▼
              Found             Not Found
                 │                 │
                 ▼                 ▼
             Product         Replenishment
                              manual flow
```

Este diseño deja el catálogo preparado para que el siguiente bloque pueda implementar la **persistencia real y la constraint de unicidad `(tenant_id, barcode)`**, sin tener que modificar las reglas de dominio.
