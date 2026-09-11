La idea es que V10 deje el backend listo para que posteriormente Flutter pueda consumirlo sin introducir lógica de negocio en la aplicación móvil.

V10 — feat(vending): establish replenishment execution context
Objetivo

Formalizar el contexto de ejecución de una reposición que necesita el cliente móvil:

Replenisher
    ↓
identify machine
    ↓
capture execution context
    ├── machine
    ├── actor
    ├── tenant
    ├── timestamp
    └── location
    ↓
add replenishment lines
    ↓
complete

V10 debe resolver correctamente:

identificación de máquina;
validación de que la máquina pertenece al tenant;
validación de que el replenisher puede operar sobre ella;
captura de ubicación al iniciar la operación;
captura temporal de cada línea;
consulta de slots disponibles;
consulta de información necesaria para capturar productos;
preparación del backend para QR/barcode sin acoplarlo a Flutter;
mantener toda la lógica de negocio en Application/Domain.

No debe implementar todavía el cliente Flutter.

Arquitectura

La arquitectura queda:

Flutter / futuro cliente móvil
             │
             ▼
       FastAPI / HTTP
             │
             ▼
       Application
             │
       ┌─────┴─────┐
       ▼           ▼
     Domain    Platform
       │       Context/Auth/
       │       Tenant/Idempotency/
       │       Transaction
       ▼
 Persistence
       │
       ▼
 PostgreSQL

El principio fundamental:

El móvil captura datos; Vending decide si la operación es válida.

Por ejemplo, el móvil puede enviar:

{
  "machine_id": "...",
  "location": {
    "latitude": -35.4264,
    "longitude": -71.6554,
    "accuracy_m": 12.4
  }
}

pero el móvil no decide que tiene autorización para operar esa máquina.

1. Machine Identification

Agregar un contrato de identificación de máquina preparado para QR.

No haría que el dominio dependa de una cámara, scanner o librería QR.

Por ejemplo:

MachineIdentifier
├── machine_id
├── identifier_type
└── identifier_value

Tipos iniciales:

INTERNAL_ID
QR_CODE

La resolución sería:

scanned QR
     ↓
MachineIdentifier
     ↓
Machine

El QR es solamente un mecanismo de identificación.

Regla

No:

QRCodeService

dentro del Domain.

Sí:

HTTP/mobile input
       ↓
ResolveMachine
       ↓
MachineRepository
2. Resolve Machine

Agregar el caso de uso:

ResolveMachine

Responsabilidades:

recibir identificador;
obtener la máquina;
validar tenant;
validar estado de la máquina;
validar autorización del actor;
devolver información operacional mínima.

Respuesta conceptual:

{
  "machine_id": "...",
  "identifier": "...",
  "machine_type": "SNACK",
  "name": "...",
  "status": "ACTIVE",
  "slots": [...]
}

No debería devolver información administrativa innecesaria.

3. Machine → Replenisher Authorization

Aquí hay una distinción importante.

No basta con:

machine.tenant_id == context.tenant_id

Debe existir una regla que permita determinar:

¿Este replenisher puede realizar operaciones sobre esta máquina?

V10 puede establecer el contrato:

MachineAccessPolicy

o equivalente dentro de Application/Domain.

Inicialmente podría existir una asignación:

Replenisher
    ↓
MachineAssignment
    ↓
Machine

con:

replenisher_id
machine_id
tenant_id
valid_from
valid_until
status

Esto evita que el API termine haciendo:

if user.role == "REPLENISHER":
    ...

como regla de negocio dispersa.

4. Replenishment Execution Context

V10 debe formalizar el contexto capturado al comenzar una reposición.

Conceptualmente:

ReplenishmentExecutionContext
├── tenant_id
├── replenisher_id
├── machine_id
├── started_at
└── location

La ubicación:

Location
├── latitude
├── longitude
└── accuracy_m

Opcionalmente:

captured_at

pero el timestamp oficial de la operación debe seguir siendo controlado por el backend.

5. GPS no debe convertirse en una regla implícita

Esto es importante para no acoplar Vending prematuramente a geofencing.

V10 captura y persiste ubicación, pero no necesariamente implementa:

"solo puede reponer si está a menos de 50 metros"

Eso sería otra regla de negocio.

Por lo tanto:

GPS capture
    ≠
GPS authorization

V10 deja preparado el contrato para que posteriormente pueda existir:

MachineLocationPolicy

sin modificar la arquitectura.

6. Machine Slots

V10 debería formalizar la consulta operacional de slots.

El móvil necesita conocer:

Machine
 ├── Slot 01
 │    ├── capacity
 │    ├── current quantity
 │    ├── preferred product
 │    └── price
 │
 ├── Slot 02
 ...

Esto permite que el usuario pueda seleccionar:

Máquina
 ↓
Slot
 ↓
Producto
 ↓
Cantidad

y no depender de conocimiento previo del layout físico.

Importante

La respuesta debe diferenciar:

preferred_product

de:

actual product

porque V8 estableció que el producto realmente cargado pertenece a la ReplenishmentLine.

7. Product Lookup para captura móvil

V10 debería agregar el contrato de búsqueda de producto necesario para el flujo de reposición.

Caso de uso:

FindProductByBarcode

Flujo:

barcode
   ↓
ProductRepository
   ↓
found?
 ├── yes → Product
 └── no  → PRODUCT_NOT_FOUND

El backend no debe permitir crear automáticamente un Product porque el barcode no existe.

El flujo posterior será responsabilidad de la aplicación:

scan
 ↓
not found
 ↓
rescan
 ↓
not found
 ↓
manual description

Pero el producto manual debe quedar claramente diferenciado de:

Product catalog

Esto evita contaminar el catálogo con productos introducidos accidentalmente desde terreno.

8. Add Replenishment Line

V9 ya tenía:

POST /replenishments/{id}/lines

V10 debe endurecer el contrato para que una línea valide:

machine
slot
product
quantity
price
capacity
inventory
authorization

Y especialmente:

slot belongs to machine
product exists
quantity > 0
quantity <= available slot capacity
replenisher has product inventory
price is compatible
replenishment is IN_PROGRESS

La línea debe seguir registrando:

occurred_at

independientemente de:

started_at
completed_at
9. Inventory availability

Antes de agregar una línea:

Replenishment
      ↓
Product
      ↓
Replenisher inventory

debe verificarse disponibilidad.

Ejemplo:

Inventory balance = 8
Requested = 5
       ↓
allowed

pero:

Inventory balance = 3
Requested = 5
       ↓
rejected

No debe modificarse el inventario si posteriormente falla la operación completa.

Todo debe seguir dentro del mismo:

TransactionalUnitOfWork

de Platform.

10. API propuesta

La API de V9 puede evolucionar a:

Machine
GET /machines/{machine_id}
GET /machines/resolve?identifier_type=QR_CODE&value=...
Machine slots
GET /machines/{machine_id}/slots
Products
GET /products/barcode/{barcode}
Replenishment
POST /replenishments
POST /replenishments/{id}/lines
POST /replenishments/{id}/complete
POST /replenishments/{id}/cancel
GET  /replenishments/{id}

El POST /replenishments recibe:

{
  "machine_id": "...",
  "location": {
    "latitude": -35.4264,
    "longitude": -71.6554,
    "accuracy_m": 12.4
  }
}

El backend obtiene:

actor_id
tenant_id
request_id

desde RequestContext.

No desde el body.

11. Estructura propuesta
src/nexo_vending/
├── api/
│   ├── dependencies/
│   ├── routers/
│   │   ├── machines.py
│   │   ├── products.py
│   │   ├── replenishments.py
│   │   └── inventory.py
│   └── schemas/
│       ├── machines.py
│       ├── products.py
│       └── replenishment.py
│
├── application/
│   ├── use_cases/
│   │   ├── resolve_machine.py
│   │   ├── get_machine_slots.py
│   │   ├── find_product_by_barcode.py
│   │   ├── create_replenishment.py
│   │   └── add_replenishment_line.py
│   └── policies/
│       └── machine_access.py
│
├── domain/
│   ├── models/
│   │   ├── machine.py
│   │   ├── machine_slot.py
│   │   ├── machine_assignment.py
│   │   └── location.py
│   └── ports/
│       └── outbound/
│
└── infrastructure/
    ├── persistence/
    └── ...

La estructura exacta debe adaptarse a la existente; no conviene reorganizar todo el proyecto sólo por V10.

12. Tests

Este commit debe tener una suite bastante fuerte porque comienza a aparecer el verdadero flujo operacional.

Domain tests
MachineIdentifier
QR válido.
identificador vacío rechazado.
tipo desconocido rechazado.
Location
latitud válida.
longitud válida.
coordenadas fuera de rango rechazadas.
accuracy inválida rechazada.
Machine access
replenisher autorizado.
replenisher no autorizado.
asignación expirada.
asignación aún no vigente.
máquina inactiva.
Application tests
ResolveMachine
tenant A + machine A → OK
tenant A + machine B → NOT_FOUND / FORBIDDEN
GetMachineSlots
máquina inexistente;
máquina de otro tenant;
máquina sin slots;
slots correctamente asociados;
preferred product correctamente expuesto.
FindProductByBarcode
barcode existente;
barcode inexistente;
barcode perteneciente a otro tenant si el catálogo es tenant-scoped.
AddReplenishmentLine

Probar:

slot perteneciente a máquina;
slot de otra máquina;
producto existente;
producto inexistente;
cantidad positiva;
cantidad cero;
cantidad superior a capacidad;
capacidad disponible;
inventario suficiente;
inventario insuficiente;
precio compatible;
precio incompatible;
replenishment completado;
replenishment cancelado.
13. API tests

Probar como mínimo:

Authentication
no authentication → 401
Authorization
authenticated user without permission → 403
Tenant isolation
tenant A cannot access machine B
Machine resolution
valid QR → 200
unknown QR → 404
Product lookup
known barcode → 200
unknown barcode → 404
Replenishment
create → 201
add line → 201
complete → 200
Validation
invalid coordinates → 422
quantity <= 0 → 422
invalid machine → 404
invalid state → 409
14. Transaction tests con PostgreSQL/Testcontainers

Este punto es obligatorio.

No basta con mocks.

Rollback

Simular:

create replenishment
+
add line
+
inventory movement
+
failure

Resultado:

ROLLBACK

y verificar que:

replenishment
lines
inventory movements

no queden parcialmente persistidos.

Concurrency

Dos operaciones intentando llenar el mismo slot:

Slot capacity = 10
Current = 5

Transaction A → +5
Transaction B → +5

No puede terminar:

Current = 15

Debe prevalecer el control transaccional/optimistic locking ya establecido.

15. Idempotency tests

Para:

POST /replenishments
POST /replenishments/{id}/lines

probar:

same Idempotency-Key
same request
       ↓
same result
       ↓
no duplicate operation

Y:

same Idempotency-Key
different request hash
       ↓
409

Debe utilizarse exclusivamente el contrato de Platform.

No crear:

VendingIdempotencyRepository
16. Observability tests

Verificar que los casos principales emitan eventos/instrumentación mediante los contratos de Platform:

machine.resolve
replenishment.create
replenishment.line.add
product.barcode.lookup

Como mínimo:

request_id
tenant_id
actor_id
operation

deben propagarse correctamente.

No introducir directamente:

OpenTelemetry
Prometheus
Datadog
Sentry

en Vending.

17. Criterios de aceptación

V10 se considera aprobado solamente si:

1. Machine identification
 Una máquina puede ser resuelta mediante identificador.
 QR está soportado como tipo de identificador.
 El dominio no depende de ninguna librería QR.
2. Tenant isolation
 Una máquina de otro tenant no puede ser utilizada.
 No existe tenant recibido desde el body como autoridad.
 El tenant proviene de RequestContext.
3. Authorization
 Sólo un replenisher autorizado puede operar sobre una máquina.
 Asignaciones expiradas son rechazadas.
 Máquinas inactivas son rechazadas.
4. Location
 La ubicación puede registrarse al iniciar la reposición.
 Las coordenadas son validadas.
 El backend genera el timestamp oficial.
 V10 no introduce todavía geofencing obligatorio.
5. Slots
 Se pueden consultar los slots de una máquina.
 Se informa capacidad y estado necesario para la reposición.
 Se distingue configuración del slot de producto realmente cargado.
6. Barcode
 Se puede buscar un producto por barcode.
 Producto inexistente devuelve resultado estable.
 El backend no crea automáticamente productos desconocidos.
7. Replenishment
 Sólo se pueden agregar líneas a una reposición IN_PROGRESS.
 El slot debe pertenecer a la máquina.
 La cantidad respeta capacidad.
 La cantidad respeta inventario disponible.
 El precio se valida según las reglas de V8.
 Cada línea conserva su timestamp.
8. Transactionality
 Las operaciones mutables utilizan SqlAlchemyTransactionalUnitOfWork de Platform.
 No existe VendingUnitOfWork.
 No se importan módulos privados de Platform.
 Rollback probado contra PostgreSQL real/Testcontainers.
 Concurrencia probada contra PostgreSQL real/Testcontainers.
9. Idempotency
 Las operaciones mutables utilizan Platform Idempotency.
 No existen mecanismos paralelos de idempotencia en Vending.
10. Quality
 Suite completa pasa.
 Ruff pasa.
 Tests de arquitectura pasan.
 Testcontainers pasa.
 Docker smoke test pasa.
 OpenAPI se genera correctamente.
18. Documentación

Agregaría:

docs/
├── architecture/
│   ├── REPLENISHMENT_EXECUTION_CONTEXT.md
│   └── MACHINE_ACCESS.md
│
├── api/
│   ├── MACHINES_API.md
│   ├── PRODUCTS_API.md
│   └── REPLENISHMENT_EXECUTION_API.md
│
└── adr/
    └── ADR-030-replenishment-execution-context.md
REPLENISHMENT_EXECUTION_CONTEXT.md

Documentar:

Actor
Tenant
Machine
Location
Replenishment
Line

y sus responsabilidades.

MACHINE_ACCESS.md

Definir:

Tenant isolation
Machine assignment
Validity
Machine status
Authorization
MACHINES_API.md

Documentar:

GET /machines/{id}
GET /machines/resolve
GET /machines/{id}/slots
PRODUCTS_API.md

Documentar:

GET /products/barcode/{barcode}

incluyendo:

found
not found
tenant isolation
REPLENISHMENT_EXECUTION_API.md

Documentar el flujo completo:

Resolve machine
      ↓
Create replenishment
      ↓
Get slots
      ↓
Scan barcode
      ↓
Find product
      ↓
Add line
      ↓
Complete
19. ADR-030

Título:

ADR-030 — Replenishment Execution Context and Machine Access

Decisiones principales:

La máquina es el agregado operacional sobre el cual se ejecuta la reposición.
QR es un mecanismo de identificación, no una dependencia del dominio.
El tenant proviene del contexto confiable de Platform.
El acceso a una máquina se valida explícitamente.
La ubicación se captura como dato operacional.
GPS no implica todavía geofencing.
Barcode lookup consulta el catálogo pero no crea productos desconocidos.
La aplicación móvil no contiene reglas de negocio.
Transaction/UoW/Idempotency/Observability siguen siendo capacidades de Platform.
20. Exclusiones explícitas

No incluiría en V10:

❌ Flutter
❌ cámara
❌ scanner físico
❌ librería QR
❌ offline SQLite
❌ sincronización offline
❌ GPS geofencing
❌ background location
❌ push notifications
❌ Admin Web
❌ ventas
❌ coffee recipes
❌ WhatsApp
❌ Agent Core
❌ Billing

El objetivo es dejar el backend operacionalmente preparado, no comenzar todavía a construir la aplicación móvil.

21. Definition of Done

V10 está terminado cuando:

Domain
  ✓ Machine identification
  ✓ Machine access
  ✓ Location value object
  ✓ Slot execution rules

Application
  ✓ ResolveMachine
  ✓ GetMachineSlots
  ✓ FindProductByBarcode
  ✓ Replenishment execution validation

API
  ✓ Machine endpoints
  ✓ Product barcode endpoint
  ✓ Replenishment execution endpoints
  ✓ Stable errors

Platform integration
  ✓ RequestContext
  ✓ TenantContext
  ✓ Authorization
  ✓ Idempotency
  ✓ Transaction
  ✓ Observability

Persistence
  ✓ migrations
  ✓ repositories
  ✓ PostgreSQL

Tests
  ✓ unit
  ✓ application
  ✓ API
  ✓ tenant isolation
  ✓ authorization
  ✓ idempotency
  ✓ rollback
  ✓ concurrency
  ✓ Testcontainers
  ✓ architecture

Docs
  ✓ architecture
  ✓ API
  ✓ ADR

Quality
  ✓ Ruff
  ✓ pytest
  ✓ Docker
  ✓ clean install