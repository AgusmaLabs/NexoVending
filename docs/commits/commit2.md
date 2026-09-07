La idea es que al terminar V2 exista una base de dominio suficientemente sólida para que los siguientes commits puedan implementar Identity, Products, Machines, Inventory y Replenishment sin volver a discutir las reglas fundamentales.

Commit V2 — Vending Foundation & Domain Contracts
Commit message
feat(vending): establish foundation and domain contracts
Objetivo

Definir el Vending Domain Core con:

entidades;
value objects;
enums;
errores de dominio;
agregados;
contratos de repositorios;
contratos de servicios;
reglas fundamentales;
límites de dependencia;
documentación arquitectónica.

No implementar todavía persistencia real, API de negocio, autenticación Google ni aplicación móvil.

El resultado debe ser un dominio ejecutable y testeable en memoria.

1. Alcance

V2 debe establecer estos conceptos:

User / Operator
Product
Machine
MachineSlot
Replenishment
ReplenishmentLine
InventoryMovement

Pero con una distinción importante:

Identity

En V2 solamente necesitamos el contrato que Vending necesita, no implementar el sistema de identidad.

Inventory

Definimos el modelo y sus invariantes, pero no construimos todavía PostgreSQL.

Replenishment

Definimos completamente las reglas de negocio, porque será el principal caso de uso de Vending V2.

2. Arquitectura

Partiendo de tu V1:

nexo_vending/
│
├── api/
├── application/
├── domain/
└── infrastructure/

V2 debería evolucionar a:

nexo_vending/
│
├── api/
│
├── application/
│
├── domain/
│   ├── common/
│   │
│   ├── identity/
│   │
│   ├── products/
│   │
│   ├── machines/
│   │
│   ├── inventory/
│   │
│   └── replenishment/
│
└── infrastructure/

Pero no crear todavía adapters PostgreSQL para estos dominios.

3. Domain debe ser completamente independiente

La regla fundamental:

domain
   ↓
NO conoce:
FastAPI
SQLAlchemy
Alembic
PostgreSQL
Docker
HTTP
RequestContext

Incluso RequestContext de Platform debería permanecer fuera del dominio.

La integración:

Platform RequestContext
        ↓
Application
        ↓
Domain

No:

Domain → nexo-platform

Esto protege precisamente la independencia que buscas.

4. Common Domain

Crear:

domain/common/
Identificadores

Preferiría UUID:

MachineId
ProductId
UserId
ReplenishmentId
InventoryMovementId

Pueden ser aliases/value objects según el estilo que ya tengas en Platform.

5. Value Objects

V2 debería introducir algunos explícitamente.

Barcode
Barcode

Reglas:

no vacío;
longitud razonable;
normalización;
comparación exacta después de normalización.
Quantity
Quantity

Reglas:

quantity > 0

No permitir:

0
-1
GPS Coordinate
GeoLocation
latitude
longitude
accuracy

Reglas:

-90 <= latitude <= 90
-180 <= longitude <= 180
accuracy >= 0
Time

Utilizar timestamps timezone-aware.

Regla:

El dominio no debe trabajar con datetimes naive.

6. Product

Entidad:

Product

Conceptualmente:

Product
├── id
├── barcode
├── name
├── description
├── brand
├── category
├── unit
├── low_stock_threshold
└── active

Reglas:

barcode requerido
name requerido
quantity threshold >= 0

Importante:

Product no conoce Inventory ni Replenishment.

7. Machine

Entidad:

Machine
Machine
├── id
├── code
├── name
├── type
├── location
├── address
└── active

Enum:

MachineType:
    SNACK
    COFFEE

Reglas:

code obligatorio;
machine type obligatorio;
máquina inactiva no puede iniciar reposición.
8. MachineSlot

Entidad:

MachineSlot
MachineSlot
├── machine_id
├── slot_number
├── product_id
├── capacity
└── active

Reglas:

slot_number > 0
capacity > 0

Y:

MachineType.SNACK
    → slots permitidos

MachineType.COFFEE
    → slots no aplicables

Pero aquí recomiendo que MachineSlot no valide por sí mismo el tipo de máquina, porque no conoce el agregado Machine.

La validación debe estar en:

Machine

o en el servicio de dominio correspondiente.

9. Inventory

Este será uno de los elementos más importantes de V2.

InventoryMovement
InventoryMovement
id
operator_id
product_id
movement_type
quantity
reference
created_at
created_by

Enum:

InventoryMovementType:
    ASSIGNMENT
    REPLENISHMENT
    RETURN
    ADJUSTMENT
    LOSS
10. No crear Inventory como CRUD mutable

No quiero:

Inventory.quantity = 50

como operación principal.

El contrato debe ser conceptualmente:

InventoryLedger
       │
       └── movements

Stock:

stock =
    SUM(ASSIGNMENT)
  + SUM(RETURN)
  + SUM(ADJUSTMENT)
  - SUM(REPLENISHMENT)
  - SUM(LOSS)

Esto prepara correctamente el terreno para auditoría.

11. Replenishment Aggregate

Este será probablemente el agregado principal de V2.

Replenishment
Replenishment
├── id
├── operator_id
├── machine_id
├── started_at
├── completed_at
├── location
├── status
└── lines[]

Estados:

ReplenishmentStatus:
    IN_PROGRESS
    COMPLETED
    CANCELLED
12. ReplenishmentLine
ReplenishmentLine
product_id
barcode_scanned
product_description_snapshot
manual_description
quantity
slot
scanned_at
13. Reglas fundamentales de Replenishment

Estas reglas deben vivir en el dominio.

No se puede crear una reposición contra máquina inactiva
inactive machine
    ↓
DomainError
No se puede agregar línea a reposición completada
COMPLETED
    ↓
cannot add line
Cantidad debe ser > 0
0 / negative
    ↓
DomainError
Snacks requieren slot
SNACK + no slot
    ↓
invalid
Café no utiliza slot
COFFEE + slot
    ↓
invalid
Slot debe ser válido
slot <= 0
    ↓
invalid
14. Producto desconocido

El dominio debe soportar:

product_id = None

si existe:

manual_description

Por ejemplo:

barcode_scanned = "123456"
product_id = None
manual_description = "Bebida energética X"

Pero nunca:

product_id = None
manual_description = None
15. Snapshot histórico

La línea debe conservar:

product_description_snapshot

aunque exista product_id.

Esto es importante para preservar el estado histórico.

16. Reposición como Aggregate Root

No permitiría:

replenishment.lines.append(...)

desde cualquier parte del sistema.

El agregado debería exponer:

replenishment.add_line(...)
replenishment.complete()
replenishment.cancel()

Así todas las invariantes quedan encapsuladas.

17. Contratos de repositorio

V2 debe definir interfaces, no implementaciones.

Por ejemplo:

ProductRepository
MachineRepository
ReplenishmentRepository
InventoryRepository

Conceptualmente:

class ProductRepository(Protocol):
    async def get(self, product_id): ...
    async def find_by_barcode(self, barcode): ...

Machine:

class MachineRepository(Protocol):
    async def get(self, machine_id): ...
    async def get_by_code(self, code): ...

Replenishment:

class ReplenishmentRepository(Protocol):
    async def get(self, replenishment_id): ...
    async def save(self, replenishment): ...

Inventory:

class InventoryRepository(Protocol):
    async def get_stock(self, operator_id, product_id): ...
    async def record_movement(self, movement): ...
18. Importante: Repository ≠ Service

No pondría reglas de negocio dentro de:

Repository

El repository solamente:

load
save
query

Mientras que:

Application Service
Domain

contienen la lógica.

19. Domain Services

Definiría inicialmente dos contratos.

ProductLookup
ProductLookup

Responsabilidad:

barcode
 ↓
Product | None
InventoryAvailability
InventoryAvailability

Responsabilidad:

operator
product
quantity
 ↓
available?

No implementarlos todavía contra infraestructura.

20. Caso de uso principal

V2 debería especificar el contrato:

StartReplenishment

Entrada:

operator_id
machine_id
started_at
geo_location

Resultado:

Replenishment

Después:

AddReplenishmentLine

y finalmente:

CompleteReplenishment

Esto permite que después tengamos:

REST API
Flutter
Tests

todos consumiendo la misma lógica.

21. Idempotencia

El agregado debe tener:

idempotency_key

pero la garantía de unicidad será posteriormente responsabilidad de infraestructura/persistencia.

V2 define el concepto:

Replenishment.idempotency_key

y el contrato:

ReplenishmentRepository.find_by_idempotency_key(...)

Esto prepara V2/V3 para offline sync.

22. RequestContext

Ya que V1 implementó propagación de RequestContext:

Platform
   ↓
API
   ↓
Application

mantendría esa integración.

Pero:

domain

no recibe RequestContext.

En Application:

actor_id
tenant_id
request_id

pueden transformarse en datos necesarios para ejecutar el caso de uso.

23. Multi-tenancy

Aquí haría una decisión arquitectónica ahora.

Aunque inicialmente tengas un solo negocio, Vending debería asumir:

tenant_id

como límite de aislamiento.

Pero no necesariamente lo metería en cada entidad de dominio como atributo obligatorio si Platform ya define el contexto de tenant.

La regla sería:

RequestContext.tenant_id
          ↓
Application
          ↓
Repository queries

y nunca:

WHERE tenant_id = user_input

El tenant debe venir del contexto autenticado.

Esto queda documentado como ADR.

24. Tests V2

La suite debería ser bastante completa para ser un commit de foundation.

Product tests
test_product_requires_barcode
test_product_requires_name
test_barcode_normalization
test_invalid_threshold
Machine tests
test_machine_requires_code
test_machine_type_required
test_inactive_machine
test_machine_location
Slot tests
test_slot_number_must_be_positive
test_slot_capacity_must_be_positive
test_snack_machine_accepts_slots
test_coffee_machine_does_not_accept_slots
25. Replenishment tests

Estos son los más importantes.

test_create_replenishment
test_replenishment_starts_in_progress
test_inactive_machine_rejected
test_add_product_line
test_quantity_must_be_positive
test_snack_requires_slot
test_coffee_does_not_allow_slot
test_unknown_product_requires_description
test_known_product_does_not_require_manual_description
test_completed_replenishment_cannot_add_lines
test_cancelled_replenishment_cannot_add_lines
test_complete_replenishment
test_completed_at_recorded
26. Inventory tests
test_assignment_increases_stock
test_replenishment_decreases_stock
test_return_increases_stock
test_loss_decreases_stock
test_adjustment
test_stock_calculation
test_negative_stock_rejected

Y especialmente:

test_inventory_movement_is_immutable
27. Concurrency tests

Aunque PostgreSQL todavía no se implemente, dejaría preparada la especificación de concurrencia.

Ejemplo conceptual:

stock = 10

consume 8
consume 8

El dominio debe definir:

available quantity

pero el control real de carrera quedará para el commit de persistence.

Documentarlo explícitamente evita que posteriormente alguien intente resolverlo sólo en Python.

28. Architecture tests

Aquí reutilizaría la estrategia que ya tienes.

Reglas:

domain
  ❌ api
  ❌ infrastructure
  ❌ FastAPI
  ❌ SQLAlchemy
  ❌ nexo-platform

application
  ❌ infrastructure implementation

api
  ✔ application

infrastructure
  ✔ domain
  ✔ application

Y:

domain.products
  ❌ domain.replenishment

si no existe dependencia necesaria.

29. Test de aislamiento del paquete

Como tu V1 ya tiene clean-install, agregaría una prueba específica:

pip install nexo-vending

y verificar:

import nexo_vending.domain

sin necesidad de:

PostgreSQL
Docker
environment variables

Esto demuestra que el dominio realmente es portable.

30. No tocar Alembic todavía

Este punto es importante.

V1 ya tiene:

0001_vending_bootstrap

V2 no necesita una migración nueva si todavía no persistimos estas entidades.

No crearía tablas simplemente porque ya definimos entidades de dominio.

La migración vendrá en:

V? — Persistence

Esto mantiene limpia la separación:

Domain model
        ≠
Database model
31. Documentación que debe entrar en V2

Crearía:

docs/
├── architecture/
│   ├── ARCHITECTURE.md
│   ├── DOMAIN.md
│   └── DEPENDENCIES.md
│
├── adr/
│   ├── ADR-001-vending-modular-monolith.md
│   ├── ADR-002-inventory-ledger.md
│   ├── ADR-003-replenishment-aggregate.md
│   └── ADR-004-tenant-isolation.md
│
└── api/
    └── DOMAIN_CONTRACTS.md
32. ADR-001 — Modular Monolith

Decisión:

Vending V2 será implementado como un Modular Monolith.

Razón:

baja complejidad operacional;
desarrollo rápido;
límites de dominio explícitos;
permite extraer servicios posteriormente;
compatible con Docker/VPS;
evita premature microservices.
33. ADR-002 — Inventory Ledger

Decisión:

El stock se deriva de movimientos inmutables.

Nunca:

UPDATE stock SET quantity = ...

como fuente de verdad.

Esto habilita:

auditoría;
conciliación;
ajustes;
devoluciones;
pérdidas;
inspecciones.
34. ADR-003 — Replenishment Aggregate

Decisión:

Replenishment será Aggregate Root.

Sus líneas sólo pueden modificarse mediante métodos del agregado.

Esto protege:

machine type
slot
quantity
status
product identification
35. ADR-004 — Tenant Isolation

Decisión:

Tenant es frontera de aislamiento operacional.

La aplicación obtiene tenant desde:

RequestContext

Nunca desde payload enviado por el cliente.

36. Documentación de dominio

DOMAIN.md debería contener un mapa como:

                 VENDING DOMAIN

       ┌───────────────┐
       │    Product    │
       └───────┬───────┘
               │
               │
┌──────────────▼──────────────┐
│           Machine           │
│                             │
│ ┌─────────────┐             │
│ │ MachineSlot │             │
│ └─────────────┘             │
└──────────────┬──────────────┘
               │
               ▼
      ┌─────────────────┐
      │  Replenishment  │
      │                 │
      │ ┌─────────────┐ │
      │ │    Lines    │ │
      │ └─────────────┘ │
      └────────┬────────┘
               │
               ▼
      InventoryMovement
37. Definition of Done

Consideraría Vending V2 aprobado cuando:

Domain
 Entidades definidas.
 Value Objects definidos.
 Enums definidos.
 Domain errors definidos.
 Aggregate Replenishment.
 Inventory movement model.
 Invariantes implementadas.
Contracts
 ProductRepository.
 MachineRepository.
 ReplenishmentRepository.
 InventoryRepository.
 ProductLookup.
 InventoryAvailability.
Architecture
 Domain no depende de FastAPI.
 Domain no depende de SQLAlchemy.
 Domain no depende de Platform.
 Architecture tests pasan.
 Dependencias entre módulos documentadas.
Testing
 Unit tests de entidades.
 Unit tests de value objects.
 Replenishment tests.
 Inventory tests.
 Invalid state tests.
 Idempotency contract tests.
 Architecture tests.
 Clean-install test.
 Ruff.
 Type checking, si ya forma parte del estándar del repo.
Infrastructure
 V1 Docker sigue pasando.
 V1 health sigue pasando.
 V1 readiness sigue pasando.
 V1 Testcontainers sigue pasando.
 Alembic 0001 sigue pasando.
 No se agregan tablas prematuramente.
38. Qué NO debe entrar en V2

Para mantener el commit limpio:

Funcionalidad	V2
Google OAuth real	❌
PostgreSQL repositories	❌
API de productos	❌
API de máquinas	❌
Flutter	❌
React Admin	❌
Barcode scanner	❌
QR scanner	❌
GPS hardware integration	❌
Offline sync	❌
Push notifications	❌
Low-stock alerts	❌
Alembic de dominio	❌

V2 debe responder una pregunta:

¿Tenemos un dominio Vending correctamente definido y protegido antes de empezar a construir infraestructura y UI?

V2 debe continuar exactamente esa filosofía: Vending consume Platform; no se convierte en una variante de Platform.