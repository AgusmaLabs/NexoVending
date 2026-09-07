La V1 debe cerrar el circuito usuario → máquina → producto → reposición → inventario → auditoría, dejando preparados los límites para futuras versiones.

PRD Técnico — Vending V1
1. Objetivo

Construir una plataforma para digitalizar y controlar la operación de reposición de máquinas vending, permitiendo tercerizar la operación sin perder trazabilidad sobre:

quién repuso;
qué máquina atendió;
cuándo la atendió;
dónde estaba;
qué productos llevó;
cuánto repuso;
en qué slot lo colocó;
cuánto stock recibió el reponedor;
cuánto stock debería tener;
cuánto stock realmente tiene;
diferencias y ajustes;
alertas de bajo inventario.

La V1 tendrá dos interfaces:

Mobile App: reponedores.
Admin Web: administración y control.

Y un backend único, modular y transaccional.

2. Objetivos funcionales V1
Reponedor

Debe poder:

autenticarse con Google;
consultar si su cuenta está habilitada y vigente;
identificar una máquina;
obtener GPS y hora de inicio;
realizar reposición;
escanear códigos de barras;
buscar productos;
reintentar un código no encontrado;
ingresar descripción manual cuando el producto no existe;
ingresar cantidad;
ingresar slot para snacks;
omitir slot para café;
finalizar una reposición;
consultar su stock;
visualizar operaciones pendientes de sincronización.
Administrador

Debe poder:

administrar reponedores;
asignar roles;
establecer vigencia;
administrar máquinas;
administrar slots;
administrar productos;
asignar stock a reponedores;
consultar stock;
consultar movimientos;
consultar reposiciones;
realizar ajustes;
recibir alertas de bajo stock;
auditar las operaciones.
3. Roles

Inicialmente:

Rol	Funciones
ADMIN	Control total
OPERATOR	Reposición y consulta de su stock
AUDITOR	Consulta y auditoría
SUPERVISOR	Consulta operacional

No permitiría crear roles arbitrarios en V1.

4. Regla fundamental de identidad

Autenticarse con Google no equivale a estar autorizado.

Flujo:

Google
  ↓
User
  ↓
¿Existe?
 ├─ NO → PENDING
 └─ SI
      ↓
¿Activo?
      ↓
¿Rol?
      ↓
¿Vigencia?
      ↓
ACCESS

El administrador controla:

valid_from
valid_until
active
role
5. Máquina

Cada máquina tendrá:

machine_code
name
type
latitude
longitude
address
active

Tipos:

SNACK
COFFEE

Cada máquina tendrá un QR único.

Ejemplo:

VM-000123

El QR no debería contener información sensible; simplemente un identificador de máquina.

6. Identificación de máquina

El flujo principal será:

Reponer
   ↓
Escanear QR
   ↓
GET machine
   ↓
Validar máquina activa
   ↓
Obtener GPS
   ↓
Registrar timestamp
   ↓
Crear Replenishment

Se guardará:

started_at
latitude
longitude
accuracy

La precisión GPS es importante.

No basta con:

lat/lon

porque posteriormente quieres determinar si realmente estaba en la máquina.

7. Reposición

Una reposición representa una visita del reponedor a una máquina.

Replenishment

Estados:

IN_PROGRESS
COMPLETED
CANCELLED

Ejemplo:

Replenishment
------------------
id
machine_id
operator_id
started_at
completed_at
latitude
longitude
gps_accuracy
status
idempotency_key
created_at
8. Líneas de reposición

Cada producto repuesto genera una línea.

ReplenishmentLine

Campos:

id
replenishment_id
product_id
barcode_scanned
product_description_snapshot
quantity
slot
scanned_at
created_at
¿Por qué guardar product_description_snapshot?

Porque el catálogo puede cambiar.

Si hoy:

Coca-Cola 350 ml

mañana cambia a:

Coca-Cola Original 350ml

la reposición histórica debe seguir mostrando exactamente qué se registró en ese momento.

9. Producto no encontrado

Este flujo debe ser explícito:

scan barcode
     ↓
lookup
     ↓
found?
 ├── YES
 │    ↓
 │ product
 │
 └── NO
      ↓
   retry scan
      ↓
   lookup
      ↓
   found?
    ├── YES
    │
    └── NO
         ↓
   manual description

La descripción manual no crea automáticamente un Product.

La línea queda:

product_id = NULL
manual_description = "Bebida energética X"

Esto permitirá posteriormente que el administrador resuelva el producto.

10. Stock del reponedor

Este será un dominio central.

No almacenaría solamente:

operator.product.stock

como fuente de verdad.

La fuente de verdad será:

InventoryMovement

Tipos:

ASSIGNMENT
REPLENISHMENT
RETURN
ADJUSTMENT
LOSS

Ejemplo:

+100 ASSIGNMENT
-20  REPLENISHMENT
-10  REPLENISHMENT
+5   RETURN
-2   LOSS
----------------
73 stock
11. Asignación de productos

El administrador puede entregar productos a un reponedor:

Juan
Coca-Cola
Cantidad: 100

Se genera:

InventoryMovement
type = ASSIGNMENT
quantity = +100

Y:

Stock
Coca-Cola = 100
12. Reposición y descuento de inventario

Cuando el reponedor confirma:

8 Coca-Cola

el backend debe ejecutar una transacción:

BEGIN

create replenishment
create replenishment_line

create inventory_movement
    type = REPLENISHMENT
    quantity = -8

COMMIT

Nunca:

reposición OK
...
después intentar descontar stock

Debe ser una sola operación transaccional.

13. Invariante de inventario

El backend debe impedir:

stock < 0

salvo que explícitamente decidamos introducir posteriormente una política de inventario negativo.

Para V1:

No se permite stock negativo.

Si Juan tiene:

5 Coca-Cola

y intenta registrar:

8 Coca-Cola

la operación debe ser rechazada.

14. Auditoría

Todo movimiento de inventario debe quedar trazable.

Ejemplo:

InventoryMovement
-----------------
id
operator_id
product_id
quantity
type
reference_type
reference_id
created_at
created_by

Así podemos responder:

¿Por qué Juan tiene 23 Coca-Cola?

Y obtener:

01/09 +50 asignación
02/09 -10 reposición VM-01
02/09 -8  reposición VM-03
03/09 -9  reposición VM-05
15. Stock bajo

Cada producto puede tener:

low_stock_threshold

Por ejemplo:

Coca-Cola
threshold = 10

Si:

stock <= 10

se genera una alerta.

No la generaría desde el frontend.

El backend es la autoridad.

16. Máquina y slots

Para snacks:

Machine
   │
   └── MachineSlot
          │
          └── Product

Ejemplo:

VM-001
├── Slot 1 → Coca-Cola
├── Slot 2 → Sprite
├── Slot 3 → Agua
└── Slot 4 → Snickers

Para café:

VM-002
type = COFFEE

no requiere slots.

17. Reglas de slots

Backend:

SNACK → slot obligatorio
COFFEE → slot NULL

Además:

slot debe existir en la máquina

y:

slot debe estar activo

Esto no debe depender exclusivamente del frontend.

18. Modelo entidad-relación

La primera versión quedaría aproximadamente así:

                         ┌─────────────┐
                         │    USER     │
                         ├─────────────┤
                         │ id          │
                         │ email       │
                         │ google_sub  │
                         │ active      │
                         └──────┬──────┘
                                │
                         ┌──────▼──────────┐
                         │ OPERATOR_ASSIGN │
                         ├─────────────────┤
                         │ user_id         │
                         │ role            │
                         │ valid_from      │
                         │ valid_until     │
                         └─────────────────┘
                                │
              ┌─────────────────┴──────────────────┐
              │                                    │
              ▼                                    ▼
       ┌──────────────┐                    ┌────────────────┐
       │ REPLENISHMENT│                    │ INVENTORY_MOVE │
       ├──────────────┤                    ├────────────────┤
       │ id           │                    │ id             │
       │ operator_id  │                    │ operator_id    │
       │ machine_id   │                    │ product_id     │
       │ started_at   │                    │ type           │
       │ completed_at │                    │ quantity       │
       │ GPS          │                    │ reference_id   │
       └──────┬───────┘                    └───────┬────────┘
              │                                    │
              ▼                                    │
       ┌──────────────┐                            │
       │ REPLENISHMENT│                            │
       │     LINE     │                            │
       ├──────────────┤                            │
       │ product_id   │◄───────────────────────────┘
       │ quantity     │
       │ slot         │
       │ scanned_at   │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │   PRODUCT    │
       ├──────────────┤
       │ id           │
       │ barcode      │
       │ name         │
       │ category     │
       └──────────────┘

       ┌──────────────┐
       │   MACHINE    │
       ├──────────────┤
       │ id           │
       │ code         │
       │ type         │
       │ latitude     │
       │ longitude    │
       └──────┬───────┘
              │
              ▼
       ┌──────────────┐
       │ MACHINE_SLOT │
       ├──────────────┤
       │ id           │
       │ machine_id   │
       │ slot_number  │
       │ product_id   │
       └──────────────┘
19. Tablas principales
users
id UUID PK
email VARCHAR UNIQUE
name VARCHAR
google_subject VARCHAR UNIQUE
active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
operator_assignments
id UUID PK
user_id UUID FK
role VARCHAR
valid_from TIMESTAMP
valid_until TIMESTAMP
active BOOLEAN
created_at TIMESTAMP
products
id UUID PK
barcode VARCHAR UNIQUE
name VARCHAR
description TEXT
brand VARCHAR
category VARCHAR
unit VARCHAR
low_stock_threshold INTEGER
active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
machines
id UUID PK
code VARCHAR UNIQUE
name VARCHAR
type VARCHAR
latitude NUMERIC
longitude NUMERIC
address TEXT
active BOOLEAN
created_at TIMESTAMP
updated_at TIMESTAMP
machine_slots
id UUID PK
machine_id UUID FK
slot_number INTEGER
product_id UUID FK NULL
capacity INTEGER NULL
active BOOLEAN
UNIQUE(machine_id, slot_number)
replenishments
id UUID PK
machine_id UUID FK
operator_id UUID FK
status VARCHAR
started_at TIMESTAMP
completed_at TIMESTAMP
latitude NUMERIC
longitude NUMERIC
gps_accuracy NUMERIC
idempotency_key UUID UNIQUE
created_at TIMESTAMP
replenishment_lines
id UUID PK
replenishment_id UUID FK
product_id UUID NULL
barcode_scanned VARCHAR
product_description_snapshot TEXT
manual_description TEXT NULL
quantity INTEGER
slot INTEGER NULL
scanned_at TIMESTAMP
created_at TIMESTAMP
inventory_movements
id UUID PK
operator_id UUID FK
product_id UUID FK
movement_type VARCHAR
quantity INTEGER
reference_type VARCHAR
reference_id UUID
created_at TIMESTAMP
created_by UUID
20. API V1

Usaría:

/api/v1

y nunca endpoints sin versión.

Authentication
POST /auth/google

Entrada:

{
  "id_token": "..."
}

Respuesta:

{
  "access_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "...",
    "name": "Juan",
    "role": "OPERATOR",
    "status": "ACTIVE"
  }
}
21. Current user
GET /me

Respuesta:

{
  "id": "...",
  "name": "Juan Pérez",
  "email": "juan@example.com",
  "role": "OPERATOR",
  "active": true,
  "valid_until": "2026-09-30T23:59:59Z"
}
22. Products
GET /products/barcode/{barcode}

Respuesta:

{
  "id": "...",
  "barcode": "7801234567890",
  "name": "Coca-Cola 350ml",
  "brand": "Coca-Cola",
  "category": "BEVERAGE"
}

Si no existe:

404

La aplicación realiza el segundo intento.

23. Machines
GET /machines/{machine_id}

Respuesta:

{
  "id": "...",
  "code": "VM-001",
  "name": "Clínica Andes",
  "type": "SNACK",
  "latitude": -35.426,
  "longitude": -71.655,
  "active": true
}
GET /machines/{machine_id}/slots
{
  "machine_id": "...",
  "slots": [
    {
      "slot": 1,
      "product_id": "...",
      "product_name": "Coca-Cola 350ml",
      "capacity": 10
    }
  ]
}
24. Crear reposición
POST /replenishments

Headers:

Authorization: Bearer ...
Idempotency-Key: UUID

Body:

{
  "machine_id": "...",
  "latitude": -35.426,
  "longitude": -71.655,
  "gps_accuracy": 8.5
}

Respuesta:

{
  "id": "...",
  "status": "IN_PROGRESS",
  "machine_id": "...",
  "started_at": "2026-09-04T19:30:00Z"
}
25. Agregar línea
POST /replenishments/{id}/lines

Snacks:

{
  "product_id": "...",
  "barcode_scanned": "7801234567890",
  "quantity": 8,
  "slot": 14
}

Café:

{
  "product_id": "...",
  "barcode_scanned": "7801234567890",
  "quantity": 8
}

El backend valida:

machine.type
26. Producto no encontrado

La API debe permitir:

{
  "product_id": null,
  "barcode_scanned": "123456789",
  "manual_description": "Bebida energética X",
  "quantity": 5,
  "slot": 12
}

No debe permitir:

product_id = null
manual_description = null
27. Completar reposición
POST /replenishments/{id}/complete

Respuesta:

{
  "id": "...",
  "status": "COMPLETED",
  "completed_at": "2026-09-04T19:45:12Z"
}

En este punto debe quedar cerrada la transacción de inventario.

28. Stock del reponedor
GET /me/inventory

Respuesta:

{
  "items": [
    {
      "product_id": "...",
      "barcode": "7801234567890",
      "product_name": "Coca-Cola 350ml",
      "quantity": 42,
      "low_stock": false
    }
  ]
}
29. Movimientos
GET /me/inventory/movements

Filtros:

product_id
from
to
movement_type

Respuesta:

{
  "items": [
    {
      "product": "Coca-Cola 350ml",
      "type": "ASSIGNMENT",
      "quantity": 50,
      "created_at": "..."
    },
    {
      "product": "Coca-Cola 350ml",
      "type": "REPLENISHMENT",
      "quantity": -8,
      "reference_id": "..."
    }
  ]
}
30. Administración
GET /admin/operators
POST /admin/operators/{id}/assignment
{
  "role": "OPERATOR",
  "valid_from": "2026-09-01T00:00:00Z",
  "valid_until": "2026-09-30T23:59:59Z"
}
31. Asignación de stock
POST /admin/inventory/assignments
{
  "operator_id": "...",
  "product_id": "...",
  "quantity": 100,
  "note": "Entrega turno septiembre"
}

Resultado:

InventoryMovement
ASSIGNMENT +100
32. Consulta administrativa de stock
GET /admin/operators/{id}/inventory
{
  "operator": {
    "id": "...",
    "name": "Juan"
  },
  "items": [
    {
      "product": "Coca-Cola",
      "assigned": 100,
      "replenished": 73,
      "returned": 5,
      "adjustments": 0,
      "loss": 2,
      "expected_stock": 20
    }
  ]
}

Esto es precisamente lo que necesitas para la auditoría.

33. Auditoría
GET /admin/audit

Filtros:

operator
machine
product
event_type
from
to

Ejemplo:

GET /admin/audit?
operator_id=...
&machine_id=...
&from=...
&to=...
34. Errores API

Establecería desde V1 un formato estándar:

{
  "error": {
    "code": "INSUFFICIENT_STOCK",
    "message": "Insufficient stock for product",
    "details": {
      "available": 5,
      "requested": 8
    }
  }
}

Códigos:

UNAUTHORIZED
FORBIDDEN
USER_NOT_ACTIVE
USER_ASSIGNMENT_EXPIRED
MACHINE_NOT_FOUND
MACHINE_INACTIVE
PRODUCT_NOT_FOUND
INVALID_SLOT
INSUFFICIENT_STOCK
REPLENISHMENT_NOT_FOUND
REPLENISHMENT_ALREADY_COMPLETED
IDEMPOTENCY_CONFLICT
35. Arquitectura de módulos Backend

Aquí recomiendo ser bastante estricto:

vending/
│
├── identity/
│   ├── domain/
│   ├── application/
│   ├── ports/
│   └── adapters/
│
├── operators/
│
├── products/
│
├── machines/
│
├── inventory/
│
├── replenishment/
│
├── audit/
│
├── notifications/
│
└── shared/

Cada dominio tendrá:

domain
application
ports
adapters
36. Dependencias entre módulos

Regla:

identity
   ↑
operators
   ↑
inventory
   ↑
replenishment

Pero evitar:

replenishment → SQLAlchemy
replenishment → FastAPI
inventory → HTTP
domain → PostgreSQL

El dominio no sabe que existe PostgreSQL.

37. Mobile Architecture

Flutter:

mobile/
│
├── lib/
│   ├── core/
│   │   ├── auth/
│   │   ├── network/
│   │   ├── scanner/
│   │   ├── gps/
│   │   ├── storage/
│   │   └── sync/
│   │
│   ├── features/
│   │   ├── authentication/
│   │   ├── replenishment/
│   │   ├── inventory/
│   │   └── profile/
│   │
│   └── main.dart
38. Offline-first

Lo incorporaría en la arquitectura aunque la primera versión pueda funcionar online.

El móvil tendrá:

SQLite

para operaciones pendientes.

Estado:

DRAFT
PENDING_SYNC
SYNCING
SYNCED
SYNC_ERROR

Ejemplo:

Replenishment
     ↓
SQLite
     ↓
PENDING_SYNC
     ↓
Internet
     ↓
API
     ↓
SYNCED

Esto es especialmente importante para vending.

39. Sincronización

La aplicación nunca debería asumir:

POST → 200

como único escenario.

Puede ocurrir:

POST
 ↓
server procesa
 ↓
respuesta perdida
 ↓
mobile cree que falló
 ↓
retry

Por eso:

Idempotency-Key

es obligatorio.

40. Admin Frontend

Para el backoffice utilizaría:

React
TypeScript

con una estructura:

admin/
│
├── auth/
├── dashboard/
├── operators/
├── machines/
├── products/
├── inventory/
├── replenishments/
└── audit/

No mezclaría el código de administración con Flutter.

41. Infraestructura de desarrollo
Docker Compose
│
├── api
├── postgres
├── redis
└── admin

En testing:

pytest
Testcontainers
PostgreSQL real

La base de datos de producción no se replica con SQLite.

42. Infraestructura de producción V1
                     INTERNET
                         │
                    Cloudflare
                         │
                       HTTPS
                         │
                    Reverse Proxy
                         │
              ┌──────────┴──────────┐
              │                     │
          Admin Web              API
                                    │
                           ┌────────┴────────┐
                           │                 │
                       PostgreSQL          Redis
                           │
                         Backup

Inicialmente puede vivir en un VPS con Docker Compose.

No Kubernetes.

No microservicios.

43. Observabilidad

Desde V1:

structured logs
request_id
correlation_id
health check
metrics
error tracking

Endpoints:

GET /health
GET /ready

Y registrar:

request_id
user_id
endpoint
duration
status

Nunca registrar tokens ni información sensible.

44. Seguridad

Mínimos V1:

HTTPS obligatorio;
JWT/session segura;
validación Google token en backend;
autorización server-side;
roles;
vigencia;
rate limiting;
CORS restringido;
secretos mediante environment/secrets;
PostgreSQL no expuesto públicamente;
backups;
audit trail;
idempotencia.
45. Tests de aceptación críticos

Hay algunos tests que considero bloqueantes para aprobar V1.

Identidad
Google login válido
Google login inválido
usuario pendiente
usuario deshabilitado
usuario expirado
rol insuficiente
Producto
barcode encontrado
barcode no encontrado
segundo intento
manual description
Máquina
QR válido
QR inexistente
máquina inactiva
snack
café
Reposición
snack requiere slot
café no requiere slot
slot inexistente
cantidad inválida
timestamp
GPS
Inventario
assignment +100
replenishment -10
stock correcto
stock insuficiente
stock no negativo
Concurrencia

Especialmente:

stock = 10

request A → consume 8
request B → consume 8

El resultado correcto debe ser:

una operación aprobada
una rechazada
stock = 2

Nunca:

stock = -6
Idempotencia

Enviar dos veces:

Idempotency-Key = ABC

debe producir un solo descuento.

46. Criterios de aceptación globales

Consideraría V1 aprobada solamente cuando:

Funcional
 Reponedor puede autenticarse con Google.
 Admin puede habilitar/deshabilitar usuarios.
 Existe vigencia de acceso.
 Máquina puede identificarse mediante QR.
 GPS queda registrado.
 Timestamp queda registrado.
 Producto puede identificarse mediante barcode.
 Existe segundo intento.
 Se permite descripción manual.
 Snacks requieren slot.
 Café no requiere slot.
 Cada línea tiene timestamp.
 Reposición queda cerrada.
 Stock se descuenta.
 No existe stock negativo.
 Admin puede asignar stock.
 Admin puede consultar stock.
 Existe trazabilidad de movimientos.
 Existe alerta de bajo stock.
Técnica
 PostgreSQL.
 Alembic.
 Docker.
 Testcontainers.
 CI/CD.
 Tests unitarios.
 Tests integración.
 Tests de concurrencia.
 Tests de idempotencia.
 API versionada.
 Arquitectura modular.
 Domain aislado de infraestructura.
47. Evolución prevista

La arquitectura deja espacio para:

V1
Reposición
   ↓
V2
Rutas + planificación
   ↓
V3
Stock máquina
   ↓
V4
Ventas / telemetría
   ↓
V5
Optimización de inventario
   ↓
V6
Predicción de demanda
   ↓
V7
Agente IA Vending

Y ahí aparece nuevamente la arquitectura que has estado construyendo:

                  NEXO PLATFORM
                       │
             ┌─────────┴─────────┐
             │                   │
        PLATFORM CORE        AGENT CORE
             │                   │
             │                   ▼
             │             Vending Agent
             │                   │
             │              Tools/Policies
             │                   │
             └──────────┬────────┘
                        ▼
                  VENDING DOMAIN
                        │
             ┌──────────┼──────────┐
             │          │          │
          Machine    Inventory   Replenishment
             │          │          │
             └──────────┼──────────┘
                        ▼
                   PostgreSQL

Esta sería mi arquitectura objetivo: Vending no necesita convertirse ahora en un microservicio ni contaminar Agent Core. Es un bounded context de negocio modular, que consume la infraestructura transaccional que ya construiste.