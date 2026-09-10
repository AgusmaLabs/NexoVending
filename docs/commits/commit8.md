# Commit V8 — Inventory Ledger & Transactional Replenishment

## 1. Commit message

```text
feat(vending): establish inventory ledger and transactional replenishment
```

## 2. Objetivo

Implementar el dominio de **Inventory y Replenishment** de NexoVending, utilizando la infraestructura transaccional pública de:

```text
nexo-platform >= 1.3.0
```

El commit debe permitir:

* asignar productos al stock de un reponedor
* registrar movimientos de inventario
* consultar stock
* iniciar una reposición
* registrar productos realmente cargados en slots
* permitir sustituciones de SKU
* respetar capacidad física del slot
* registrar precio efectivamente aplicado
* completar/cancelar reposiciones
* ejecutar Replenishment + Inventory de manera atómica
* soportar idempotencia
* soportar concurrencia real
* preservar aislamiento multi-tenant

## 3. Principio arquitectónico

V8 debe respetar estrictamente:

```text
Product
   │
   │ catálogo
   ▼

MachineSlot
   │
   ├── preferred_product
   ├── capacity
   └── selling_price
   │
   │ configuración
   ▼

Replenishment
   │
   ├── actual_product
   ├── quantity
   └── applied_price
   │
   │ operación
   ▼

Inventory Ledger
   │
   └── movements
```

La regla es:

> **Machine configura. Replenishment opera. Inventory registra.**

## 4. Dependencia de Platform

Actualizar Vending para consumir:

```text
nexo-platform >= 1.3.0
```

y utilizar exclusivamente la API pública:

```python
from nexo_platform.transaction import (
    TransactionalUnitOfWork,
    SqlAlchemyTransactionalUnitOfWork,
)
```

o:

```python
from nexo_platform import (
    TransactionalUnitOfWork,
    SqlAlchemyTransactionalUnitOfWork,
)
```

No utilizar:

```python
nexo_platform.persistence.sqlalchemy...
```

ni ningún módulo privado de persistencia.

## 5. Composición transaccional

La composición correcta será:

```text
Vending Composition Root
        │
        ├── SQLAlchemy Session
        │
        ├── Vending repositories
        │
        └── SqlAlchemyTransactionalUnitOfWork
                         │
                         ▼
                  same Session
```

Ejemplo conceptual:

```python
session = create_session()

async with SqlAlchemyTransactionalUnitOfWork(session) as uow:
    replenishment_repo = ...
    inventory_repo = ...

    # mismos session/repositories
    ...
```

La UoW de Platform **no crea otra Session**.

## 6. Responsabilidad de TransactionalUnitOfWork

Vending debe utilizar la UoW para:

* commit
* rollback
* flush
* atomicidad

No debe implementar una segunda abstracción genérica equivalente.

La responsabilidad queda:

```text
Platform
    → transaction boundary

Vending
    → business transaction

SQLAlchemy adapter
    → persistence
```

## 7. BillingUnitOfWork

No utilizar:

```python
BillingUnitOfWork
```

en Vending.

Billing sigue siendo una especialización de Platform independiente de Vending.

Vending debe utilizar:

```text
TransactionalUnitOfWork
```

general.

Esto mantiene:

```text
Platform Transaction
       ▲
       │
 ┌─────┴─────┐
 │           │
Billing    Vending
```

sin introducir conocimiento de Billing en Vending.

## 8. Inventory Ledger

Crear:

```text
InventoryMovement
```

como registro inmutable de una modificación de inventario.

Tipos iniciales:

```text
ASSIGNMENT
REPLENISHMENT
RETURN
ADJUSTMENT
LOSS
```

## 9. InventoryMovement

Campos conceptuales:

```text
MovementId
tenant_id
product_id
quantity
movement_type
reference_type
reference_id
actor_id
occurred_at
idempotency_key
metadata
```

El movimiento debe ser históricamente interpretable.

No modificar movimientos existentes para representar nuevos estados.

## 10. Significado de quantity

La convención debe ser única y documentada.

Recomiendo:

```text
ASSIGNMENT       +10
RETURN            +5
ADJUSTMENT        +3
REPLENISHMENT     -8
LOSS              -1
```

Por tanto:

```text
balance = SUM(movements.quantity)
```

Esto simplifica el cálculo y evita reglas distintas por tipo de movimiento.

## 11. Inventory Balance

El balance debe derivarse del ledger.

No crear como fuente independiente:

```text
Product.stock
```

ni:

```text
Replenisher.stock
```

como valores desconectados del ledger.

Puede existir un balance materializado posteriormente por rendimiento, pero debe mantenerse dentro de la misma transacción y nunca convertirse en una segunda fuente de verdad.

## 12. Inventory Scope

Inventory debe soportar inicialmente:

```text
Tenant
   │
   └── Product
          │
          └── Inventory Movements
```

El stock del reponedor debe poder distinguirse mediante el contexto de asignación/custodia.

La implementación concreta debe evitar mezclar:

```text
stock general
```

con:

```text
stock bajo custodia del reponedor
```

## 13. Inventory Assignment

Crear operación:

```text
AssignInventory
```

Ejemplo:

```text
Replenisher R1

Coca-Cola +50
Agua +30
```

Esto genera movimientos:

```text
ASSIGNMENT +50
ASSIGNMENT +30
```

y debe quedar asociado al actor/reponedor correspondiente.

## 14. Replenishment Aggregate

Crear:

```text
Replenishment
```

como Aggregate Root.

Campos conceptuales:

```text
ReplenishmentId
tenant_id
machine_id
replenisher_id
started_at
completed_at
status
location
idempotency_key
lines
```

## 15. ReplenishmentStatus

```text
IN_PROGRESS
COMPLETED
CANCELLED
```

Transiciones:

```text
IN_PROGRESS → COMPLETED
IN_PROGRESS → CANCELLED
```

Una reposición completada o cancelada no puede recibir nuevas líneas.

## 16. ReplenishmentLine

Cada línea representa **lo que efectivamente se cargó**.

```text
LineId
slot_id
product_id
quantity
unit_price
occurred_at
product_description_snapshot
preferred_product_id_snapshot?
replacement_reason?
```

La línea no debe asumir que:

```text
product_id == MachineSlot.preferred_product_id
```

## 17. Preferred vs Actual Product

Ejemplo:

```text
MachineSlot
preferred_product = Coca-Cola
```

pero:

```text
ReplenishmentLine
actual_product = Sprite
```

Esto es válido.

La configuración del slot no se modifica automáticamente.

## 18. Product Snapshot

Guardar:

```text
product_description_snapshot
```

y, si corresponde:

```text
preferred_product_id_snapshot
```

Esto permite reconstruir históricamente:

```text
qué se esperaba
qué se cargó
qué descripción tenía el producto
```

aunque el catálogo cambie posteriormente.

## 19. Precio

La línea registra:

```text
unit_price
```

como precio efectivamente aplicado.

No reconstruir precios históricos consultando:

```text
MachineSlot.selling_price
```

porque este puede cambiar.

Ejemplo:

```text
2026-01
Slot price = 1500

2026-06
Slot price = 1700
```

Una reposición de enero debe seguir mostrando:

```text
unit_price = 1500
```

## 20. Regla de sustitución

Debe soportarse:

```text
preferred = Coca-Cola
actual = Sprite
price = 1500
```

cuando ambos corresponden al mismo precio operacional.

La sustitución debe quedar registrada como tal.

No modificar:

```text
preferred_product_id
```

del slot.

## 21. Sustitución con precio diferente

Si:

```text
preferred price = 1500
actual price = 1700
```

no debe producirse una sustitución silenciosa.

Debe existir una operación explícita que permita el cambio de precio/configuración según las reglas comerciales que definamos.

V8 debe impedir que una diferencia de precio sea escondida como una sustitución normal.

## 22. Slot sin producto preferido

Si:

```text
preferred_product = NULL
```

el reponedor puede seleccionar un producto disponible.

Ejemplo:

```text
Slot 8
capacity = 10
preferred = NULL

Replenishment:
Agua × 10
```

válido.

## 23. Capacidad del slot

La cantidad a cargar debe respetar:

```text
quantity_to_add
    <=
slot.capacity - current_quantity
```

donde `current_quantity` proviene de Inventory/estado operacional.

Ejemplo:

```text
capacity = 10
current = 3

maximum replenishment = 7
```

## 24. Stock disponible

También debe respetarse:

```text
quantity_to_add <= replenisher_available_stock
```

Por lo tanto:

```text
quantity =
min(
    free_slot_capacity,
    available_inventory,
    requested_quantity
)
```

El dominio no debe permitir stock negativo.

## 25. Objetivo "máquina llena"

V8 debe permitir que la operación de reposición maximice la carga:

```text
fill as much as possible
```

dentro de:

* capacidad
* stock disponible
* reglas de precio
* reglas de sustitución

No implementar todavía un optimizador automático de surtido.

## 26. Cambio de capacidad

Si V5 cambia:

```text
capacity 12 → 8
```

y existe:

```text
current stock = 10
```

V8 **no debe crear automáticamente**:

```text
LOSS -2
```

La capacidad y el inventario son conceptos distintos.

Debe quedar:

```text
capacity = 8
stock = 10
```

hasta que una operación explícita determine qué hacer con el excedente.

## 27. CompleteReplenishment

Este es el caso transaccional principal.

Conceptualmente:

```text
CompleteReplenishment
        │
        ├── load Replenishment
        ├── validate status
        ├── validate Machine
        ├── validate Slots
        ├── validate Products
        ├── validate capacity
        ├── validate inventory
        │
        ├── persist Replenishment
        │
        ├── create InventoryMovement(s)
        │
        └── complete Replenishment
                 │
                 ▼
               COMMIT
```

Todo debe utilizar la misma Session.

## 28. Atomicidad

Debe garantizarse:

```text
Replenishment COMPLETED
        +
Inventory movements created
```

o:

```text
ROLLBACK
```

Nunca:

```text
Replenishment COMPLETED
Inventory unchanged
```

ni:

```text
Inventory decremented
Replenishment still IN_PROGRESS
```

## 29. Uso de flush

La aplicación puede utilizar:

```python
await uow.flush()
```

cuando necesite detectar errores de persistencia antes del commit.

Debe quedar documentado:

> `flush()` no constituye commit.

Por lo tanto:

```text
write
↓
flush
↓
error
↓
rollback
```

sigue siendo completamente reversible.

## 30. Commit/Rollback

Delegar el lifecycle a:

```text
SqlAlchemyTransactionalUnitOfWork
```

Comportamiento esperado:

```text
success
    → flush
    → commit
```

```text
exception
    → rollback
```

```text
commit failure
    → rollback
    → re-raise
```

Vending no debe duplicar esta lógica.

## 31. Nested UoW

Vending no debe intentar crear una segunda UoW sobre la misma Session.

Debe respetar la regla de Platform:

```text
NestedTransactionError
```

Esto debe probarse en tests de integración.

## 32. Concurrencia

Debe utilizarse la infraestructura de concurrencia existente en Platform.

En particular:

* optimistic locking
* detección de conflicto
* manejo de `40P01`
* manejo de `40001`
* retry cuando corresponda

Pero:

> estas capacidades pertenecen a la infraestructura transaccional y no al dominio de Inventory.

## 33. Retry Policy

No implementar una nueva `RetryPolicy` dentro de Vending.

Cuando sea necesario reintentar una operación transaccional:

```text
Vending Application
       ↓
Platform transactional/reliability capability
```

El dominio no debe conocer:

```text
40P01
40001
backoff
jitter
```

## 34. Idempotencia

Cada operación de mutación debe poder identificar reintentos mediante:

```text
idempotency_key
```

La unicidad debe considerar tenant.

Conceptualmente:

```text
tenant_id + idempotency_key
```

Debe ser imposible que un retry genere dos efectos de inventario.

## 35. Idempotencia de Replenishment

Ejemplo:

```text
request A
idempotency_key = ABC123
```

produce:

```text
Replenishment R1
Inventory movement M1
```

Si llega nuevamente:

```text
request B
idempotency_key = ABC123
```

debe producir:

```text
R1
M1
```

y no:

```text
R1
M1
M2
```

## 36. Repository Ports

Definir:

```text
ReplenishmentRepository
InventoryLedgerRepository
InventoryBalanceRepository
```

si el balance requiere un port específico.

Los repositories no deben conocer HTTP, FastAPI ni Flutter.

## 37. Application Use Cases

### Replenishment

```text
CreateReplenishment
AddReplenishmentLine
CompleteReplenishment
CancelReplenishment
GetReplenishment
```

### Inventory

```text
AssignInventory
ReturnInventory
AdjustInventory
RecordLoss
GetInventoryBalance
GetInventoryMovements
```

## 38. Application Transaction Boundary

La frontera transaccional debe estar en Application.

Ejemplo conceptual:

```text
Application Use Case
       │
       ▼
TransactionalUnitOfWork
       │
       ├── MachineRepository
       ├── ProductRepository
       ├── ReplenishmentRepository
       └── InventoryRepository
```

Todos utilizando la misma Session.

## 39. Domain Independence

El Domain no debe importar:

```text
nexo_platform
SQLAlchemy
FastAPI
PostgreSQL
```

El dominio sólo conoce:

```text
entities
value objects
domain services
domain errors
repository interfaces
```

## 40. Application → Platform

Application sí puede depender de contracts públicos de Platform para:

* `RequestContext`
* transacciones
* capacidades de identidad/contexto

Pero nunca de:

```text
nexo_platform.persistence.sqlalchemy...
```

## 41. Tests de Domain

Implementar tests para:

### Replenishment

* creación
* status
* completar
* cancelar
* agregar líneas
* impedir modificación después de completar
* impedir modificación después de cancelar

### ReplenishmentLine

* quantity > 0
* unit_price válido
* snapshot
* actual product
* replacement metadata

### InventoryMovement

* tipos
* quantity
* referencias
* actor
* timestamp
* idempotency key

## 42. Tests de sustitución

Cubrir explícitamente:

```text
preferred = Coca-Cola
actual = Coca-Cola
```

→ válido.

```text
preferred = Coca-Cola
actual = Sprite
same price
```

→ válido.

```text
preferred = Coca-Cola
actual = Sprite
different price
```

→ rechazado sin cambio explícito.

```text
preferred = NULL
actual = Sprite
```

→ válido.

Y demostrar:

```text
preferred_product
```

no cambia.

## 43. Tests de capacidad

Probar:

```text
capacity = 10
stock in slot = 3
replenishment = 7
```

→ válido.

```text
capacity = 10
stock in slot = 3
replenishment = 8
```

→ rechazado.

También:

```text
capacity 12 → 8
```

con stock actual superior a la nueva capacidad.

Debe comprobarse que no se crea automáticamente un `LOSS`.

## 44. Tests de Inventory

Probar secuencia:

```text
ASSIGNMENT +100
REPLENISHMENT -20
RETURN +5
LOSS -2
ADJUSTMENT +3
```

Resultado:

```text
balance = 86
```

La fórmula debe ser:

```text
balance = SUM(movement.quantity)
```

## 45. Tests multi-tenant

Probar:

* Product de tenant A no puede utilizarse en Machine de tenant B.
* Replenishment de tenant A no puede acceder a Machine B.
* Inventory de tenant A no puede ser consumido por tenant B.
* idempotency key de tenant A no colisiona con tenant B.
* referencias históricas respetan tenant.

## 46. Tests Application + Transactional UoW

Usar:

```text
SqlAlchemyTransactionalUnitOfWork
```

real.

Verificar:

```text
uow.session is session
```

y que:

```text
Vending repository
+
Platform UoW
```

utilizan la misma Session.

## 47. Tests de commit

Probar:

```text
CompleteReplenishment
        ↓
flush
        ↓
commit
```

y verificar:

* replenishment completada
* inventory movements persistidos
* cambios visibles después del commit

## 48. Tests de rollback

Contra PostgreSQL real:

```text
CompleteReplenishment
        ↓
inventory write
        ↓
forced failure
        ↓
rollback
```

Después:

```text
Replenishment = IN_PROGRESS
Inventory = unchanged
```

No debe quedar ningún estado parcial.

## 49. Tests de commit failure

Simular/fabricar una falla de commit y verificar:

```text
rollback
+
exception re-raised
```

según el contrato de Platform 1.3.0.

## 50. Tests de nested UoW

Verificar que una segunda UoW sobre la misma Session produce:

```text
NestedTransactionError
```

y que Vending no crea accidentalmente transacciones anidadas.

## 51. Tests de concurrencia

Contra PostgreSQL/Testcontainers:

```text
Initial stock = 10

Transaction A → consume 8
Transaction B → consume 7
```

Resultado:

```text
one succeeds
one fails/retries
final stock >= 0
```

Nunca:

```text
stock = -5
```

## 52. Tests de optimistic locking

Cuando dos operaciones modifiquen el mismo recurso simultáneamente:

```text
version = N
```

una debe avanzar:

```text
version = N+1
```

y la segunda debe detectar el conflicto según la infraestructura de Platform.

## 53. Tests de idempotencia

Ejecutar dos veces:

```text
same tenant
same idempotency_key
same operation
```

y verificar:

```text
one logical replenishment
one set of inventory effects
```

No duplicar stock consumption.

## 54. Tests PostgreSQL/Testcontainers

V8 debe utilizar PostgreSQL real para las pruebas críticas de:

* transacciones
* rollback
* commit
* idempotencia
* constraints
* concurrencia
* optimistic locking
* aislamiento multi-tenant

No considerar suficiente:

```text
SQLite
```

o:

```text
mock Session
```

para estos escenarios.

## 55. Documentación

Crear/actualizar:

```text
docs/architecture/INVENTORY_AND_REPLENISHMENT.md
docs/domain/INVENTORY_RULES.md
docs/domain/REPLENISHMENT_RULES.md
docs/architecture/TRANSACTION_BOUNDARY.md

docs/adr/016-inventory-ledger.md
docs/adr/017-replenishment-as-aggregate.md
docs/adr/018-product-substitution.md
docs/adr/019-replenishment-pricing.md
docs/adr/020-transactional-completion.md
docs/adr/021-platform-transaction-uow.md
```

## 56. ADR-021 — Platform Transaction UoW

Debe documentar explícitamente:

> NexoVending no implementa una segunda abstracción genérica de Unit of Work.

Utiliza:

```text
nexo-platform >= 1.3.0
```

mediante:

```text
TransactionalUnitOfWork
SqlAlchemyTransactionalUnitOfWork
```

La Session es propiedad del composition root y se inyecta.

## 57. ADR-020 — Transactional Completion

Debe establecer:

```text
CompleteReplenishment
```

como una única unidad transaccional:

```text
Replenishment state change
+
Inventory movements
```

utilizando la misma Session.

## 58. Fuera de alcance

V8 NO debe implementar:

* API HTTP
* Flutter
* SQLite offline queue
* sincronización offline
* Admin Web
* QR scanner
* barcode scanner
* GPS móvil
* alertas
* planificación automática
* optimización de surtido
* predicción de demanda
* ventas
* facturación
* pagos

Tampoco debe implementar una nueva:

```text
UnitOfWork
RetryPolicy
OptimisticLocking
```

si esas capacidades ya existen en Platform.

## 59. Criterios de aceptación

El commit se considera aprobado solamente si:

1. Vending depende de `nexo-platform >= 1.3.0`.
2. Utiliza `TransactionalUnitOfWork` público.
3. Utiliza `SqlAlchemyTransactionalUnitOfWork` como implementación SQLAlchemy.
4. No importa módulos privados de persistence de Platform.
5. Product Catalog permanece separado de Inventory.
6. MachineSlot permanece separado del stock actual.
7. Existe Inventory Ledger.
8. Existen movimientos `ASSIGNMENT`, `REPLENISHMENT`, `RETURN`, `ADJUSTMENT`, `LOSS`.
9. Existe Replenishment Aggregate.
10. Existe ReplenishmentLine.
11. La línea registra el producto realmente cargado.
12. La línea registra quantity.
13. La línea registra unit price.
14. La línea conserva snapshot histórico suficiente.
15. Preferred Product y Actual Product están separados.
16. Se permite sustitución por producto de mismo precio.
17. Sustitución con precio diferente no puede realizarse silenciosamente.
18. Un slot sin preferred product puede recibir producto.
19. No se supera la capacidad disponible.
20. No se genera stock negativo.
21. Cambio de capacidad no genera automáticamente LOSS.
22. CompleteReplenishment es atómico.
23. Rollback deja Replenishment e Inventory sin cambios parciales.
24. Vending repositories y Platform UoW comparten la misma Session.
25. `uow.session is session`.
26. Nested UoW produce `NestedTransactionError`.
27. Idempotencia evita movimientos duplicados.
28. Concurrencia real no produce stock negativo.
29. Optimistic locking funciona.
30. PostgreSQL/Testcontainers prueba los escenarios críticos.
31. Tenant isolation está probado.
32. Domain no importa Platform.
33. Application utiliza sólo APIs públicas de Platform.
34. No se duplica RetryPolicy.
35. No se duplica infraestructura transaccional.
36. Ruff pasa.
37. Suite completa pasa.
38. Documentación y ADRs están actualizados.
39. No se incorpora API/Flutter/Offline/Admin en este commit.

## 60. Definition of Done

```text
[ ] nexo-platform >= 1.3.0

[ ] InventoryMovement implementado
[ ] InventoryMovementType implementado
[ ] Inventory Ledger implementado
[ ] Inventory balance implementado/derivado

[ ] ASSIGNMENT
[ ] REPLENISHMENT
[ ] RETURN
[ ] ADJUSTMENT
[ ] LOSS

[ ] Replenishment aggregate
[ ] ReplenishmentLine
[ ] ReplenishmentStatus
[ ] product snapshot
[ ] preferred product snapshot
[ ] replacement reason
[ ] applied unit price

[ ] sustitución mismo precio
[ ] sustitución precio diferente controlada
[ ] slot vacío
[ ] capacidad respetada
[ ] stock respetado

[ ] CompleteReplenishment
[ ] CancelReplenishment
[ ] AssignInventory
[ ] ReturnInventory
[ ] AdjustInventory
[ ] RecordLoss

[ ] idempotencia
[ ] optimistic locking
[ ] concurrencia
[ ] rollback
[ ] commit failure handling

[ ] TransactionalUnitOfWork público
[ ] SqlAlchemyTransactionalUnitOfWork
[ ] misma Session
[ ] nested UoW test
[ ] sin imports privados Platform

[ ] tests Domain
[ ] tests Application
[ ] tests sustitución
[ ] tests capacidad
[ ] tests inventory
[ ] tests idempotencia
[ ] tests rollback
[ ] tests concurrencia
[ ] tests optimistic locking
[ ] tests multi-tenant
[ ] tests PostgreSQL/Testcontainers

[ ] architecture tests
[ ] Ruff limpio
[ ] suite completa pasa

[ ] INVENTORY_AND_REPLENISHMENT.md
[ ] INVENTORY_RULES.md
[ ] REPLENISHMENT_RULES.md
[ ] TRANSACTION_BOUNDARY.md
[ ] ADR-016
[ ] ADR-017
[ ] ADR-018
[ ] ADR-019
[ ] ADR-020
[ ] ADR-021

[ ] sin API
[ ] sin Flutter
[ ] sin SQLite offline
[ ] sin Admin Web
[ ] sin QR
[ ] sin GPS operacional
[ ] sin Alerting
```

## 61. Modelo final de responsabilidades

El resultado de V4–V8 debe quedar conceptualmente así:

```text
                    Product Catalog
                         │
                         │ SKU
                         ▼
                   MachineSlot
              ┌──────────┼──────────┐
              │          │          │
          preferred   capacity   price
              │
              │ configuración
              ▼
        Replenishment
              │
       ┌──────┼───────┐
       │      │       │
     slot   actual   qty
            product
              │
              ▼
       Inventory Ledger
              │
              ▼
          Stock
```

Y la regla arquitectónica fundamental:

```text
Product
  = catálogo

MachineSlot
  = configuración física/comercial

Replenishment
  = operación real

Inventory Ledger
  = evidencia de movimientos

Platform Transaction UoW
  = infraestructura de atomicidad
```

## 62. Resultado esperado

Al terminar V8 deberíamos poder ejecutar conceptualmente una operación como:

```text
Tenant: Clínica X

Machine: MIX-001

Slot 7
Preferred: Coca-Cola
Capacity: 10
Configured price: $1.500

Inventory del reponedor:
Coca-Cola = 0
Sprite = 10
```

El reponedor registra:

```text
Replenishment R001

Slot 7
Actual product: Sprite
Quantity: 10
Applied price: $1.500
Replacement reason: OUT_OF_STOCK
```

El sistema realiza en una única transacción:

```text
Replenishment R001 → COMPLETED

Inventory:
Sprite -10
```

Mientras la máquina continúa configurada:

```text
Slot 7
Preferred product = Coca-Cola
```

Si mañana vuelve a haber Coca-Cola:

```text
Replenishment R002
Coca-Cola × 10
```

sin necesidad de reconfigurar el slot.

Esto representa correctamente el negocio que describiste y deja preparada la arquitectura para V9, donde podremos exponer estas operaciones mediante API sin tener que modificar nuevamente el dominio.
