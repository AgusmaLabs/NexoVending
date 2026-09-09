# Commit V5 — Machine & Physical Slot Configuration

## 1. Commit message

```text
feat(vending): establish machine and physical slot configuration
```

## 2. Objetivo

Implementar el dominio de **Machine & Physical Slot Configuration** de NexoVending.

El modelo debe representar máquinas físicas de vending que pueden ser:

* `SNACK`
* `COFFEE`
* `MIXED`

Cada máquina puede contener **cero o más slots**, independientemente de su tipo.

Un `MachineSlot` representa una **posición/contenedor físico configurable dentro de una máquina**, no una asignación rígida de SKU.

El slot puede tener:

* posición física
* capacidad actualmente configurada
* producto preferido
* precio de venta configurado
* estado activo/inactivo

El producto preferido representa el SKU que normalmente debería ocupar el slot, pero **no constituye una restricción sobre el producto que podrá cargarse durante una reposición**.

## 3. Principios de diseño

El modelo debe mantener separadas tres dimensiones:

```text
Machine
   │
   └── Physical Slot
          │
          ├── preferred product
          ├── capacity
          └── selling price
```

frente a:

```text
Replenishment
   │
   └── actual product loaded
          ├── quantity
          ├── applied price
          └── timestamp
```

Por lo tanto:

> **Machine/Slot define configuración. Replenishment define operación.**

## 4. Machine Aggregate

Implementar:

```text
Machine
```

como Aggregate Root.

Debe contener como mínimo:

```text
MachineId
MachineCode
MachineType
MachineStatus
Location
SIIid
Slots
created_at
updated_at
```

La colección de slots pertenece al aggregate `Machine`.

No crear `MachineSlotRepository` en este commit.

## 5. MachineId

Crear Value Object propio de Vending:

```text
MachineId
```

Responsabilidades:

* identificar una máquina dentro del dominio
* garantizar formato válido
* soportar igualdad por valor
* ser independiente de Platform

No utilizar directamente identificadores de Platform como identidad de dominio.

## 6. MachineCode

Crear Value Object:

```text
MachineCode
```

Representa el código operativo de la máquina.

Reglas:

* obligatorio
* no vacío
* normalizado
* único dentro del tenant
* estable
* apto para ser utilizado posteriormente como referencia de QR

El QR no se implementa en V5.

No crear una entidad `QRCode`.

## 7. MachineType

Definir:

```python
class MachineType(Enum):
    SNACK = "SNACK"
    COFFEE = "COFFEE"
    MIXED = "MIXED"
```

### Regla fundamental

`MachineType` **NO determina si la máquina puede tener slots**.

Son válidos:

```text
SNACK  → 0..N slots
COFFEE → 0..N slots
MIXED  → 0..N slots
```

Esto debe quedar explícitamente cubierto por tests.

## 8. MachineStatus

Definir:

```python
class MachineStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    MAINTENANCE = "MAINTENANCE"
```

### Transiciones

Permitir:

```text
INACTIVE → ACTIVE
ACTIVE → INACTIVE
ACTIVE → MAINTENANCE
MAINTENANCE → ACTIVE
MAINTENANCE → INACTIVE
```

No permitir transiciones arbitrarias que dejen al aggregate en un estado inconsistente.

La política operacional de qué operaciones pueden ejecutarse según estado se resolverá posteriormente en Replenishment.

## 9. Location

Crear Value Object:

```text
Location
```

con:

```text
address
latitude
longitude
```

Esta ubicación representa la **ubicación configurada de la máquina**.

No representa el GPS capturado por el teléfono durante una reposición.

Debe quedar documentada la diferencia:

```text
Machine.location
    = ubicación configurada

Replenishment.location
    = ubicación GPS de la operación
```

## 10. MachineSlot

Crear entidad interna:

```text
MachineSlot
```

perteneciente a `Machine`.

Conceptualmente:

```text
Machine
   │
   ├── Slot 1
   ├── Slot 2
   ├── Slot 3
   └── ...
```

El slot representa:

> una posición/contenedor físico de la máquina.

No representa:

> un SKU obligatorio.

## 11. SlotId

Crear:

```text
SlotId
```

como identidad técnica del slot.

Debe diferenciarse de:

```text
slot_number
```

`SlotId` identifica la entidad.

`slot_number` identifica la posición física visible.

## 12. Slot Number

Cada slot debe tener:

```text
slot_number > 0
```

y ser único dentro de la máquina.

Ejemplo:

```text
Machine M001

Slot 1
Slot 2
Slot 3
```

No puede existir:

```text
Slot 3
Slot 3
```

dentro de la misma máquina.

## 13. Capacity

Cada slot tiene:

```text
capacity > 0
```

La capacidad representa la **capacidad física actualmente configurada** del contenedor.

Importante:

> La capacidad NO es inmutable.

Puede cambiar debido a modificaciones físicas como:

* cambio de espiral
* cambio de configuración del contenedor
* cambio de formato
* adaptación a otra demanda

Ejemplo:

```text
Slot 5
capacity = 12
```

Después:

```text
cambio de espiral
```

puede convertirse en:

```text
Slot 5
capacity = 8
```

La operación de cambiar capacidad pertenece al dominio de Machine/Slot.

## 14. Capacidad no equivale a stock

Debe quedar explícitamente prohibido interpretar:

```text
slot.capacity
```

como:

```text
slot.current_stock
```

Ejemplo:

```text
capacity = 10
current stock = 3
```

El stock será responsabilidad del futuro Inventory Domain.

V5 solamente conoce la capacidad física configurada.

## 15. Preferred Product

El slot puede tener:

```text
preferred_product_id
```

opcional.

Puede ser:

```text
NULL
```

Esto representa:

> el SKU que normalmente se espera encontrar en este slot.

No significa:

> el único SKU que puede colocarse.

### Ejemplo

```text
Slot 7
preferred_product = Coca-Cola
```

Durante una reposición futura podría cargarse:

```text
Sprite
```

sin modificar necesariamente:

```text
preferred_product = Coca-Cola
```

La decisión operacional de sustitución pertenece a Replenishment.

## 16. No imponer compatibilidad SKU → Slot

V5 **no debe implementar** reglas como:

```text
Slot 7 solo acepta Coca-Cola
```

ni:

```text
Slot 7 acepta Coca-Cola o Sprite
```

ni:

```text
Slot 7 solo acepta productos de categoría X
```

La configuración del slot establece una preferencia, no una restricción operacional.

## 17. Selling Price

El slot debe poder tener:

```text
selling_price
```

como configuración comercial de la posición.

El precio **no pertenece al Product Catalog**.

Esto permite:

```text
Machine A
Slot 1 → Coca-Cola → $1.500

Machine B
Slot 1 → Coca-Cola → $1.700
```

El mismo SKU puede tener distintos precios según la máquina.

## 18. Precio y producto preferido

El precio configurado del slot debe interpretarse como:

```text
precio de venta configurado para esa posición
```

No como:

```text
Product.price
```

y tampoco como:

```text
precio histórico de cada reposición
```

El precio efectivamente aplicado durante una reposición deberá quedar registrado por Replenishment.

## 19. Configuración vs operación

Esta separación debe quedar explícita:

```text
MachineSlot
──────────────────────────
preferred_product_id
capacity
selling_price
active
```

mientras que posteriormente:

```text
ReplenishmentLine
──────────────────────────
machine_id
slot_id
product_id
quantity
unit_price
timestamp
```

Esto permite que:

```text
preferred product = Coca-Cola
```

pero una reposición concreta sea:

```text
actual product = Sprite
```

sin corromper la configuración de la máquina.

## 20. Slot Lifecycle

Un slot debe poder estar:

```text
ACTIVE
INACTIVE
```

Un slot inactivo representa una posición física temporalmente fuera de servicio.

No eliminar físicamente slots mediante operaciones normales del dominio si posteriormente han participado en operaciones.

Para V5 puede implementarse:

```text
add_slot()
activate_slot()
deactivate_slot()
```

La eliminación física, si se considera necesaria, debe tratarse como una decisión posterior relacionada con persistencia/historial.

## 21. Machine Aggregate Behaviors

Implementar comportamiento equivalente a:

```text
create()
activate()
deactivate()
put_in_maintenance()

add_slot()
activate_slot()
deactivate_slot()

change_slot_capacity()
set_preferred_product()
clear_preferred_product()
set_slot_selling_price()

find_slot()
```

Todas las modificaciones de slots deben pasar por `Machine`.

No exponer mutaciones directas de la colección interna.

## 22. Product Assignment

La configuración:

```text
set_preferred_product(slot, product)
```

debe verificar que el producto:

* existe
* pertenece al mismo tenant
* está activo

Pero **no debe verificar que el producto pueda o no ser cargado operacionalmente en ese slot**.

Esa decisión corresponde a Replenishment.

## 23. Tenant Isolation

Machine y Slot pertenecen a un tenant.

La identidad del tenant debe provenir de:

```text
Platform RequestContext
```

en Application/API.

Nunca:

```text
request.tenant_id
```

proporcionado libremente por el cliente.

Flujo:

```text
Platform RequestContext
        ↓
Application
        ↓
Machine use case
        ↓
Domain
```

El Domain no importa `nexo_platform`.

## 24. Application Ports

Definir:

```text
MachineRepository
```

como port.

Debe operar sobre:

```text
Machine
```

y no sobre modelos ORM.

Use cases mínimos:

```text
CreateMachine
UpdateMachine
ActivateMachine
DeactivateMachine
PutMachineInMaintenance

AddMachineSlot
ActivateMachineSlot
DeactivateMachineSlot

ChangeSlotCapacity
SetPreferredProduct
ClearPreferredProduct
SetSlotSellingPrice

GetMachine
FindMachineByCode
ListMachineSlots
```

## 25. Platform Integration

Vending debe consumir:

```text
nexo-platform==1.2.0
```

cuando corresponda.

Utilizar las capacidades existentes de Platform para:

* `RequestContext`
* `Principal`
* identidad/autenticación
* tenant context

No implementar nuevamente:

* Google OAuth
* JWT
* Principal
* AuthenticationProvider
* tenant authentication
* autorización de identidad

## 26. Tests de Domain

### MachineId

Probar:

* creación válida
* valores inválidos
* igualdad
* estabilidad

### MachineCode

Probar:

* creación válida
* vacío
* normalización
* igualdad
* valores inválidos

### MachineType

Probar:

```text
SNACK
COFFEE
MIXED
```

### MachineStatus

Probar:

* transiciones válidas
* transiciones inválidas

### Location

Probar:

* ubicación válida
* coordenadas inválidas
* valores límite

## 27. Tests de MachineSlot

Probar:

* `SlotId`
* slot number válido
* slot number cero
* slot number negativo
* capacidad válida
* capacidad cero
* capacidad negativa
* estado activo
* estado inactivo
* preferred product opcional
* selling price válido

## 28. Tests de Machine + Slots

Probar explícitamente:

```text
SNACK + slots
COFFEE + slots
MIXED + slots
```

Todos deben ser válidos.

Además:

* agregar slot
* detectar slot duplicado
* buscar slot
* activar slot
* desactivar slot
* cambiar capacidad
* establecer producto preferido
* eliminar producto preferido
* establecer precio

## 29. Tests de capacidad dinámica

Debe existir una prueba explícita:

```text
capacity = 12
        ↓
change_slot_capacity(8)
        ↓
capacity = 8
```

Y demostrar que:

* la operación es válida
* no modifica el `SlotId`
* no modifica el `slot_number`
* no modifica el producto preferido
* no modifica el precio

Esto refleja el caso real de cambio de espiral.

## 30. Tests de flexibilidad de SKU

Debe existir una prueba que demuestre:

```text
preferred_product = Coca-Cola
```

y que el dominio **no impone** que futuras operaciones deban utilizar Coca-Cola.

El test no debe implementar todavía Replenishment.

Su objetivo es demostrar que Machine no contiene esa restricción.

## 31. Tests de precio

Probar:

```text
Product A
Machine 1 / Slot 1 → $1.500

Product A
Machine 2 / Slot 1 → $1.700
```

Demostrando que el precio no pertenece al Product.

También:

* precio válido
* precio inválido
* cambio de precio
* independencia del producto preferido

## 32. Application Tests

Probar:

* creación de Machine
* recuperación
* actualización
* lifecycle
* creación de slots
* cambio de capacidad
* configuración de SKU preferido
* configuración de precio
* aislamiento por tenant
* rechazo de Product de otro tenant
* rechazo de Product inactivo
* propagación de `RequestContext`

## 33. Architecture Tests

Mantener:

```text
domain
    MUST NOT import
        nexo_platform
        fastapi
        sqlalchemy
        postgres
```

Application puede consumir contracts de Platform cuando sea necesario.

Infrastructure puede depender de:

```text
domain
application
PostgreSQL
SQLAlchemy
Platform adapters
```

El objetivo es preservar la independencia del dominio.

## 34. Documentación

Crear/actualizar:

```text
docs/architecture/MACHINE_MANAGEMENT.md
docs/domain/MACHINE_AND_SLOT_RULES.md
docs/adr/011-machine-as-aggregate.md
docs/adr/012-machine-types.md
docs/adr/013-slot-as-physical-container.md
docs/adr/014-slot-preferred-product.md
docs/adr/015-slot-capacity-and-pricing.md
```

### MACHINE_MANAGEMENT.md

Debe explicar:

* Machine Aggregate
* MachineType
* MachineStatus
* Location
* MachineSlot
* relación Machine → Slot
* configuración vs operación

### MACHINE_AND_SLOT_RULES.md

Debe contener las invariantes del dominio.

Especialmente:

```text
MachineType no determina existencia de slots.
```

```text
Slot representa posición/contenedor físico.
```

```text
preferred_product no restringe el producto que podrá cargarse.
```

```text
capacity es configurable y mutable.
```

```text
capacity != stock.
```

```text
selling_price pertenece al contexto MachineSlot.
```

## 35. ADR-011 — Machine como Aggregate Root

Justificar:

```text
Machine
  └── MachineSlot
```

en lugar de:

```text
MachineRepository
SlotRepository
```

La razón es que las invariantes de los slots dependen de la máquina:

* slot number único
* pertenencia al tenant
* lifecycle
* configuración

## 36. ADR-012 — Machine Types

Documentar:

```text
SNACK
COFFEE
MIXED
```

y la decisión:

> El tipo de máquina no restringe la cantidad ni existencia de slots.

## 37. ADR-013 — Slot como Physical Container

Documentar la decisión:

> Un slot representa una posición/contenedor físico y no una asignación rígida de SKU.

Esto permite representar:

* máquinas de snacks
* máquinas de café
* máquinas mixtas
* cambios de configuración física

## 38. ADR-014 — Preferred Product

Documentar:

> `preferred_product_id` representa el SKU normalmente esperado en el slot, pero no constituye una restricción operacional.

Ejemplo:

```text
Slot 7
preferred = Coca-Cola
```

Una reposición posterior podrá utilizar otro SKU según las reglas de Replenishment.

## 39. ADR-015 — Capacity and Pricing

Documentar dos decisiones:

### Capacity

La capacidad representa la configuración física actual y puede cambiar.

### Pricing

El precio de venta pertenece al contexto Machine/Slot y no al Product Catalog.

## 40. Fuera de alcance

Este commit NO debe implementar:

* Inventory
* stock actual
* movimientos de inventario
* Replenishment
* sustitución de productos
* regla "mismo precio"
* regla "slot vacío → cualquier producto"
* cantidad cargada en slot
* historial de producto cargado
* historial de stock
* sincronización offline
* QR scanner
* GPS operacional
* API HTTP
* persistencia PostgreSQL
* Alembic
* Google OAuth
* JWT
* roles
* permisos
* alertas

## 41. Criterios de aceptación

El commit se considera aprobado solamente si:

1. `MachineType` soporta `SNACK`, `COFFEE` y `MIXED`.
2. Cualquier tipo de máquina puede tener cero o más slots.
3. No existe la regla `COFFEE → no slots`.
4. `MachineSlot` representa una posición/contenedor físico.
5. `slot_number` es único dentro de Machine.
6. `slot_number > 0`.
7. `capacity > 0`.
8. `capacity` puede modificarse posteriormente.
9. Cambiar capacity no cambia la identidad del slot.
10. `preferred_product_id` es opcional.
11. `preferred_product_id` no constituye una restricción de carga.
12. Un producto preferido debe pertenecer al mismo tenant.
13. Un producto inactivo no puede configurarse como producto preferido.
14. El precio pertenece al slot/configuración de máquina y no al Product.
15. El precio puede modificarse.
16. Machine controla sus slots como Aggregate Root.
17. No existe `MachineSlotRepository`.
18. El Domain no depende de Platform.
19. Application obtiene el tenant desde Platform `RequestContext`.
20. No se duplica autenticación/Google OAuth/JWT.
21. Existen tests explícitos para SNACK + slots.
22. Existen tests explícitos para COFFEE + slots.
23. Existen tests explícitos para MIXED + slots.
24. Existe test de cambio de capacidad por cambio de espiral.
25. Existe test que demuestra que preferred SKU no es una restricción operacional.
26. Existe test de precios independientes del Product.
27. Existen tests de aislamiento multi-tenant.
28. Architecture tests pasan.
29. Ruff pasa sin errores.
30. La suite completa existente continúa pasando.
31. La documentación y ADRs reflejan el modelo actualizado.
32. No se introduce Inventory ni Replenishment.

## 42. Definition of Done

```text
[ ] Machine aggregate implementado
[ ] MachineId implementado
[ ] MachineCode implementado
[ ] MachineType SNACK / COFFEE / MIXED
[ ] MachineStatus implementado
[ ] Location implementado

[ ] MachineSlot implementado
[ ] SlotId implementado
[ ] slot_number validado
[ ] capacity validada
[ ] capacity mutable
[ ] preferred_product_id opcional
[ ] preferred_product no restrictivo
[ ] selling_price implementado
[ ] slot lifecycle implementado

[ ] Machine controla sus slots
[ ] MachineRepository definido
[ ] Application use cases implementados

[ ] RequestContext integrado
[ ] tenant isolation validado
[ ] Domain independiente de Platform

[ ] tests unitarios
[ ] tests de invariantes
[ ] tests de capacidad dinámica
[ ] tests de preferred product
[ ] tests de pricing
[ ] tests multi-tenant
[ ] architecture tests

[ ] MACHINE_MANAGEMENT.md
[ ] MACHINE_AND_SLOT_RULES.md
[ ] ADR-011
[ ] ADR-012
[ ] ADR-013
[ ] ADR-014
[ ] ADR-015

[ ] Ruff limpio
[ ] suite completa pasa

[ ] sin Inventory
[ ] sin Replenishment
[ ] sin API
[ ] sin PostgreSQL
[ ] sin QR
[ ] sin GPS operacional
```

## 43. Modelo conceptual definitivo de V5

```text
                    Machine
                       │
                       │ 1..*
                       ▼
                  MachineSlot
                       │
          ┌────────────┼────────────┐
          │            │            │
          ▼            ▼            ▼
    slot_number     capacity    selling_price
                         │
                         │
                  preferred_product
                         │
                         ▼
                      Product
```

Pero esta relación debe interpretarse como:

```text
preferred_product
       =
SKU habitual/configurado
```

y NO:

```text
preferred_product
       =
único SKU permitido
```

La operación futura será:

```text
Machine
   │
   └── Slot
         │
         ├── configured/preferred SKU
         │
         └── actual SKU loaded
                    │
                    ▼
              Replenishment
```

## 44. Regla arquitectónica que debe quedar establecida

La regla más importante que deja V5 para los siguientes commits es:

> **Machine configura el espacio físico y sus parámetros. Replenishment decide qué producto se carga. Inventory registra cuánto stock existe.**

Esto permite soportar directamente los casos reales:

```text
Slot habitual: Coca-Cola
Producto disponible: Sprite
Precio igual
→ Replenishment puede sustituir.
```

```text
Slot vacío
→ Replenishment puede decidir otro producto.
```

```text
Cambio de espiral
12 unidades → 8 unidades
→ MachineSlot cambia capacity.
```

sin contaminar Machine con reglas que realmente pertenecen a la operación.
