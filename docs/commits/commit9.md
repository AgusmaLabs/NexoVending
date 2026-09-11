Sí. Considerando que V8 ya quedó implementado y validado, y tomando como base el alcance que quedó definido para V8 —donde HTTP/API, Flutter, offline y Admin quedaron explícitamente fuera—, el siguiente paso natural es V9: exponer los casos de uso mediante una API HTTP, sin introducir lógica de negocio nueva.

La idea es que V9 sea principalmente un adapter de entrada, conectando HTTP → Application → Domain.

V9 — API de Replenishment e Inventory
1. Commit message
feat(vending): expose inventory and replenishment application API
2. Objetivo

Exponer mediante FastAPI las operaciones de negocio que ya existen en V8:

HTTP
  ↓
API
  ↓
Application Use Cases
  ↓
Domain
  ↓
Vending Repositories
  ↓
Platform Transaction UoW
  ↓
PostgreSQL

V9 no debe agregar nuevas reglas de negocio.

Su objetivo es convertir los casos de uso existentes en una interfaz HTTP estable y preparada para:

aplicación móvil del reponedor;
futuro Admin Web;
integraciones futuras.
3. Arquitectura

La dirección debe quedar:

FastAPI
   ↓
API / HTTP Adapter
   ↓
Application
   ↓
Domain
   ↓
Infrastructure

Y Platform transversal:

                    Nexo Platform
                         │
        ┌────────────────┼────────────────┐
        │                │                │
 RequestContext      Transaction       Idempotency
 TenantContext          UoW             Observability
        │                │                │
        └────────────────┼────────────────┘
                         │
                         ▼
                    Nexo Vending
                         │
                  Application API
                         │
                    Domain
                         │
                  Persistence
4. Principio fundamental

FastAPI no debe contener reglas de negocio.

Incorrecto:

@router.post("/replenishments")
async def create(...):
    if quantity > slot.capacity:
        ...

Correcto:

@router.post("/replenishments")
async def create(...):
    command = CreateReplenishmentCommand(...)
    return await create_replenishment.execute(command)

Las validaciones de negocio continúan perteneciendo a Domain/Application.

5. Endpoints iniciales

Yo limitaría V9 a las operaciones necesarias para el flujo de reposición.

Replenishment
POST   /replenishments
GET    /replenishments/{id}
POST   /replenishments/{id}/lines
POST   /replenishments/{id}/complete
POST   /replenishments/{id}/cancel
Inventory
POST   /inventory/assignments
GET    /inventory/balance
GET    /inventory/movements
POST   /inventory/returns
POST   /inventory/adjustments
POST   /inventory/losses

No expondría todavía endpoints de ventas, porque ese flujo puede evolucionar independientemente.

6. Identidad y Tenant

V9 debe integrar el contexto de Platform.

La cadena será:

HTTP Authorization
        ↓
Authentication Adapter
        ↓
Principal
        ↓
RequestContext
        ↓
TenantContext
        ↓
Application

La API no debe aceptar tenant_id como autoridad desde el body.

Por ejemplo, evitar:

{
  "tenant_id": "tenant-a",
  "machine_id": "machine-1"
}

como mecanismo para decidir el tenant.

El tenant confiable proviene de:

RequestContext / TenantContext

según el contrato de Platform.

7. Autorización

Los endpoints deben utilizar las capacidades de Platform.

Por ejemplo, conceptualmente:

replenishment.create
replenishment.complete
inventory.assign
inventory.return
inventory.adjust
inventory.loss
inventory.read

Los códigos concretos deben definirse en Vending, porque Platform establece que:

Permission / Entitlement codes → Product.

Platform proporciona el mecanismo; Vending define qué permisos necesita.

8. Entitlements

También debemos diferenciar:

Permission

de:

Entitlement

Por ejemplo:

Permission:
replenishment.create

Entitlement:
vending.replenishment

La autorización responde:

¿Este usuario puede ejecutar esta operación?

El entitlement responde:

¿Este producto/tenant tiene habilitada esta capacidad?

No deben mezclarse.

9. DTOs HTTP

Crear schemas específicos para API.

Por ejemplo:

api/schemas/
├── replenishment.py
├── inventory.py
└── common.py

No exponer directamente entidades Domain como modelos Pydantic/FastAPI.

La separación debería ser:

HTTP DTO
   ↓
Application Command
   ↓
Domain

y:

Domain Result
   ↓
Application Result
   ↓
HTTP Response DTO
10. Create Replenishment

Request conceptual:

{
  "machine_id": "...",
  "location": {
    "latitude": -35.42,
    "longitude": -71.65
  }
}

Pero ojo:

V9 puede transportar ubicación; no debe introducir todavía reglas GPS.

El backend simplemente debe pasar el dato al caso de uso si el dominio ya lo soporta.

11. Add Replenishment Line

Request:

{
  "slot_id": "...",
  "product_id": "...",
  "quantity": 8
}

La aplicación obtiene/configura:

MachineSlot
Product
preferred product
capacity
current inventory
price

y el dominio determina si la operación es válida.

No confiar en valores enviados por el cliente para:

capacity
price
preferred_product
12. Sustitución

La API debe permitir expresar explícitamente una sustitución.

Por ejemplo:

{
  "slot_id": "...",
  "product_id": "sprite",
  "quantity": 10,
  "replacement_reason": "OUT_OF_STOCK"
}

Pero la API no debe decidir si la sustitución es válida.

Debe delegarlo al dominio.

13. Complete Replenishment

Este endpoint es particularmente importante:

POST /replenishments/{id}/complete

Debe terminar ejecutando:

CompleteReplenishment

dentro de la frontera transaccional existente.

HTTP
 ↓
CompleteReplenishment
 ↓
Platform TransactionalUoW
 ├── Replenishment
 └── Inventory movements
 ↓
COMMIT

No crear una transacción adicional en el controller.

14. Idempotencia HTTP

Aquí V9 debe aprovechar lo que V8 ya preparó.

Las operaciones mutables deben aceptar:

Idempotency-Key: abc-123

Por ejemplo:

POST /replenishments
Idempotency-Key: 01J...

y:

POST /replenishments/R1/complete
Idempotency-Key: 01J...

La API transporta la clave.

Platform IdempotencyService sigue siendo responsable de la protección.

No crear:

VendingIdempotencyService

ni otra tabla de idempotencia.

15. Manejo de errores

V9 debe establecer un mapping consistente:

Domain error
       ↓
Application error
       ↓
HTTP exception

Por ejemplo:

Situación	HTTP
JSON inválido	422
recurso inexistente	404
estado inválido	409
capacidad insuficiente	409
stock insuficiente	409
sustitución inválida	409
tenant no autorizado	403/404 según política
autenticación ausente	401
error inesperado	500

Los códigos exactos deben quedar centralizados en el adapter HTTP.

16. Error response

Definir un formato estable, por ejemplo:

{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "Insufficient inventory for replenishment",
    "request_id": "..."
  }
}

El request_id debe provenir del contexto de Platform.

No devolver stack traces.

17. Observabilidad

V9 debe integrar:

Platform Observability

y no introducir:

OpenTelemetry SDK
Prometheus SDK
Datadog SDK

directamente en Vending.

Conceptualmente:

obs.logger.info(
    "replenishment.complete.started",
    context=context,
)

y:

request_id
tenant_id
principal_id
operation

deben acompañar la operación.

18. Feature Flags

No usaría feature flags para esconder lógica de dominio.

Sí pueden utilizarse para seleccionar versiones de implementación:

replenishment.api.v2

si en algún momento existe una segunda versión.

Pero:

feature flag != permission
feature flag != entitlement

tal como ya quedó establecido en Platform.

19. Tests de API

V9 debe agregar una suite específica:

tests/api/
├── test_replenishments.py
├── test_inventory.py
├── test_authentication.py
├── test_authorization.py
├── test_errors.py
└── test_idempotency.py
Replenishment

Probar:

crear;
obtener;
agregar línea;
completar;
cancelar;
estado inválido;
recurso inexistente;
sustitución;
capacidad;
stock.
20. Tests de autorización

Probar:

authenticated + permission
        → allowed

y:

authenticated + no permission
        → 403

También:

tenant A principal
+
resource tenant B
        ↓
denied
21. Tests de autenticación

Probar:

no credentials
    → 401
valid Principal
    → RequestContext

Y comprobar que Application recibe el contexto correcto.

El dominio debe continuar sin conocer autenticación.

22. Tests de idempotencia HTTP

Este grupo es obligatorio.

Enviar dos veces:

POST /replenishments/R1/complete
Idempotency-Key: ABC

Resultado:

first request  → executes
second request → same logical result

y comprobar:

Inventory movements = 1

no:

Inventory movements = 2
23. Tests de tenant isolation

Con PostgreSQL/Testcontainers:

Tenant A
  └── Machine A
      └── Replenishment A

Tenant B
  └── Machine B

Intentar:

Tenant A → GET Replenishment B

debe fallar.

Y:

Tenant A → add line to Replenishment B

también.

Esto debe comprobarse a través de HTTP, no solamente mediante repositories.

24. Tests transaccionales end-to-end

Uno de los tests más importantes:

HTTP POST complete
        ↓
Application
        ↓
Vending repositories
        ↓
Platform UoW
        ↓
PostgreSQL

Verificar que:

Replenishment COMPLETED
+
Inventory movement

se persisten conjuntamente.

Y ante una falla:

HTTP
 ↓
Complete
 ↓
forced persistence failure
 ↓
ROLLBACK

no queda estado parcial.

25. Tests de concurrencia

No repetir toda la suite de V8.

V9 debe comprobar que dos requests HTTP concurrentes que afectan el mismo recurso respetan las garantías ya establecidas:

Request A ──┐
            ├── PostgreSQL
Request B ──┘

Resultado:

one succeeds
one conflicts/retries/fails

según la política de Platform.

26. OpenAPI

La API debe generar documentación OpenAPI automáticamente mediante FastAPI.

Pero debemos considerar OpenAPI como contrato HTTP, no como modelo de dominio.

Documentar:

endpoints;
request schemas;
response schemas;
errores;
autenticación;
idempotency;
códigos HTTP.
27. Estructura propuesta

La estructura podría quedar:

src/nexo_vending/
├── api/
│   ├── dependencies/
│   │   ├── auth.py
│   │   ├── context.py
│   │   └── database.py
│   │
│   ├── routers/
│   │   ├── replenishments.py
│   │   └── inventory.py
│   │
│   ├── schemas/
│   │   ├── replenishment.py
│   │   ├── inventory.py
│   │   └── errors.py
│   │
│   └── error_handlers.py
│
├── application/
│   └── ...
│
├── domain/
│   └── ...
│
└── infrastructure/
    └── persistence/
        └── ...

La API es únicamente un inbound adapter.

28. Tests arquitectónicos

Agregar reglas:

api
  → application
  → platform public API

api
  ✕ domain infrastructure details

domain
  ✕ api

domain
  ✕ fastapi

domain
  ✕ nexo_platform

api
  ✕ nexo_platform.persistence internals

Y especialmente:

api
  ✕ SQLAlchemy repositories directly

La API debe pasar por Application.

29. Documentación

Crearía:

docs/architecture/API_ARCHITECTURE.md
docs/api/REPLENISHMENT_API.md
docs/api/INVENTORY_API.md
docs/api/ERRORS.md
docs/api/IDEMPOTENCY.md

Y un ADR:

docs/adr/ADR-029-vending-http-api-boundary.md
ADR-029

Debe dejar establecido:

FastAPI es un adapter de entrada. No contiene reglas de negocio ni accede directamente a repositories. Toda operación atraviesa Application.

30. Qué NO incluir en V9

Mantendría fuera:

❌ Flutter
❌ QR
❌ Barcode scanner
❌ GPS enforcement
❌ Offline SQLite
❌ Sync engine
❌ Admin Web
❌ WhatsApp
❌ Instagram
❌ Facebook
❌ Push notifications
❌ Background workers
❌ Sales API
❌ Billing

Especialmente no incorporaría todavía la lógica de scanner. El backend debe recibir product_id/slot_id; será responsabilidad de la aplicación móvil obtener esos datos mediante cámara posteriormente.

31. Criterios de aceptación

V9 se considera aprobado solamente si:

Existe API HTTP para Replenishment.
Existe API HTTP para Inventory.
FastAPI actúa exclusivamente como inbound adapter.
Controllers no contienen reglas de negocio.
Controllers no acceden directamente a repositories.
Todas las operaciones pasan por Application.
RequestContext proviene de Platform.
TenantContext proviene de Platform.
Authentication no entra al Domain.
Authorization utiliza Platform.
Permissions son definidos por Vending.
Entitlements son diferenciados de Permissions.
Idempotencia utiliza Platform.
Idempotency-Key es soportado en operaciones mutables.
No existe almacenamiento de idempotencia específico de Vending.
Errores Domain/Application tienen mapping HTTP consistente.
request_id aparece en errores.
Observabilidad utiliza contratos de Platform.
No se importan adapters concretos de observabilidad.
No se importan módulos privados de Platform.
Tenant isolation está probado vía API.
Replenishment completion sigue siendo atómico.
Rollback está probado end-to-end.
Concurrencia está probada contra PostgreSQL.
OpenAPI está generado y documentado.
Los DTO HTTP están separados del Domain.
Domain no depende de FastAPI.
Application no depende de FastAPI.
Ruff pasa.
Suite completa pasa.
PostgreSQL/Testcontainers pasa.
Arquitectura pasa.
Documentación está actualizada.
32. Definition of Done
[ ] FastAPI inbound adapter
[ ] Replenishment router
[ ] Inventory router

[ ] CreateReplenishment API
[ ] GetReplenishment API
[ ] AddReplenishmentLine API
[ ] CompleteReplenishment API
[ ] CancelReplenishment API

[ ] AssignInventory API
[ ] GetInventoryBalance API
[ ] GetInventoryMovements API
[ ] ReturnInventory API
[ ] AdjustInventory API
[ ] RecordLoss API

[ ] HTTP request DTOs
[ ] HTTP response DTOs
[ ] Error DTOs

[ ] RequestContext
[ ] TenantContext
[ ] Authentication integration
[ ] Authorization integration
[ ] Permission checks
[ ] Entitlement checks

[ ] Idempotency-Key
[ ] Platform IdempotencyService
[ ] no product-specific idempotency store

[ ] HTTP error mapping
[ ] request_id propagation
[ ] Platform Observability

[ ] API tests
[ ] authentication tests
[ ] authorization tests
[ ] tenant isolation tests
[ ] idempotency tests
[ ] rollback tests
[ ] concurrency tests
[ ] PostgreSQL/Testcontainers

[ ] OpenAPI
[ ] API documentation
[ ] ADR-029
[ ] architecture tests
[ ] Ruff
[ ] full test suite

[ ] no Flutter
[ ] no offline
[ ] no QR
[ ] no barcode
[ ] no Admin Web
[ ] no sales API
[ ] no external channel integrations