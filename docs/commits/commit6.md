# Commit 6 — `feat(vending): establish inventory, replenishment and machine consumption domain`

## 1. Objetivo

Implementar la **capa de dominio de inventario, reposición y consumo de máquinas** de NexoVending V6, definiendo las entidades, agregados, reglas de negocio y casos de uso necesarios para representar correctamente el flujo físico de productos.

Este commit debe concentrarse exclusivamente en el **modelo de dominio y sus reglas**, dejando fuera por ahora la persistencia definitiva y los mecanismos de infraestructura que serán definidos después de validar la integración con la base de datos y los servicios de la plataforma.

El objetivo es que al finalizar este commit exista un dominio coherente y testeable que permita modelar:

```text
Compra
   ↓
Administrator
   ↓
Assignment
   ↓
Replenisher
   ↓
Replenishment
   ↓
Machine / Slot
   ↓
Sale / Consumption
   ↓
Inventory reconciliation
```

---

# 2. Alcance

### Incluido

* Modelo de inventario.
* Custodia de productos.
* Movimientos de inventario.
* Aggregate `Replenishment`.
* `ReplenishmentLine`.
* Reposición y retiro de productos.
* Sustitución de productos.
* Regla de capacidad por operación.
* Precio histórico de reposición.
* Inventario esperado de Administrator.
* Inventario esperado de Replenisher.
* Inventario teórico de Machine/Slot.
* Períodos de inventario de máquinas.
* Arqueos/conteos físicos.
* Variaciones de inventario.
* Consumo de máquinas Snack.
* Consumo de máquinas Coffee mediante recetas.
* Casos de uso de dominio/aplicación necesarios.
* Reglas de negocio y validaciones.
* Tests unitarios del dominio.

### Fuera de alcance

No implementar en este commit:

* API HTTP / FastAPI.
* Endpoints `/api/v1/replenishments`.
* Endpoints `/api/v1/inventory`.
* Persistencia PostgreSQL definitiva.
* SQLAlchemy.
* Repositorios concretos.
* Migraciones de base de datos.
* Integración definitiva con la base de datos de `nexo-platform`.
* Idempotencia.
* Concurrencia.
* Multi-tenancy a nivel de infraestructura.
* Tests de integración con PostgreSQL/Testcontainers.
* Flutter/offline queue.
* Admin Web.
* Alertas.
* Automatizaciones de reposición.

La integración con `nexo-platform` deberá quedar **preparada conceptualmente**, pero no implementada hasta validar cómo debe consumirse la infraestructura existente.

---

# 3. Principios arquitectónicos

El dominio de Vending debe permanecer independiente de infraestructura.

La dirección de dependencias será:

```text
domain
   ↑
application
   ↑
infrastructure
```

El dominio:

* NO importa `nexo_platform`.
* NO importa FastAPI.
* NO importa SQLAlchemy.
* NO importa PostgreSQL.
* NO depende de detalles de persistencia.
* NO conoce `RequestContext`.
* NO conoce `UnitOfWork`.

Los contratos necesarios para persistencia o integración deberán definirse posteriormente desde la capa correspondiente.

---

# 4. Inventory Custody

El inventario debe representar **dónde está físicamente el producto**, no solamente cuánto stock existe.

Conceptualmente se consideran las siguientes ubicaciones:

```text
ADMINISTRATOR
REPLENISHER
MACHINE_SLOT
MACHINE_CONTAINER
```

Estas ubicaciones pueden materializarse posteriormente mediante la estrategia de persistencia que se defina con la plataforma.

La cadena física esperada es:

```text
Purchase
    ↓
Administrator

Assignment
    Administrator → Replenisher

Replenishment
    Replenisher → Machine

SLOT_REMOVAL
    Machine → Replenisher

Return
    Replenisher → Administrator
```

---

# 5. InventoryMovement

El inventario debe utilizar un **ledger de movimientos** como fuente de verdad para determinar el inventario esperado.

Conceptualmente:

```text
InventoryMovement
- movement_id
- product_id
- quantity
- movement_type
- reference_type
- reference_id
- occurred_at
- actor_id
- source_location
- destination_location
```

Tipos mínimos:

```text
ASSIGNMENT
REPLENISHMENT
SLOT_REMOVAL
RETURN
ADJUSTMENT
LOSS
```

### Significado

```text
ASSIGNMENT
Administrator → Replenisher

REPLENISHMENT
Replenisher → Machine

SLOT_REMOVAL
Machine → Replenisher

RETURN
Replenisher → Administrator

ADJUSTMENT
Corrección explícita de inventario

LOSS
Pérdida física confirmada
```

`SLOT_REMOVAL` debe ser diferente de `LOSS`.

Un producto retirado de una máquina para ser trasladado a otra máquina no constituye una pérdida.

---

# 6. Inventario del Administrator

El inventario esperado del Administrator debe poder calcularse directamente a partir de los movimientos conocidos.

Conceptualmente:

```text
Administrator inventory =
    purchases
  + returns received
  + adjustments
  - assignments
  - losses
```

Ejemplo:

```text
Purchase       +100
Assignment      -30
-------------------
Expected         70
```

El sistema no necesita esperar un arqueo mensual para conocer el **inventario esperado**.

Sin embargo, el inventario físico puede ser verificado mediante un conteo.

---

# 7. Inventario del Replenisher

El inventario esperado del Replenisher se calcula mediante sus movimientos de custodia.

```text
Replenisher inventory =
    assignments received
  + slot removals received
  + returns received
  - replenishments
  - returns delivered
  - losses
```

Ejemplo:

```text
Assignment       +30
Replenishment    -10
Slot removal      +3
---------------------
Expected          23
```

Al igual que para Administrator, el valor representa el **inventario esperado**, no necesariamente el inventario físico.

---

# 8. Inventario de Machine / Slot

El inventario de una máquina tiene una naturaleza diferente.

No se debe asumir que el stock físico actual es conocido permanentemente.

Para cada período:

```text
theoretical_quantity =
    opening_quantity
  + replenishments
  - consumption
```

El inventario físico se obtiene mediante un conteo/arquéo.

```text
variance =
    physical_quantity
  - theoretical_quantity
```

---

# 9. MachineInventoryPeriod

Debe existir el concepto de período de inventario de máquina.

Conceptualmente:

```text
MachineInventoryPeriod
- machine_id
- position_id
- period
- opening_quantity
- physical_quantity
- closed_at
```

### Apertura inicial

Para el primer período:

```text
opening_quantity = 0
```

No debe generarse un movimiento artificial:

```text
OPENING_BALANCE
```

### Siguiente período

Al cerrar un período:

```text
next_period.opening_quantity
    =
previous_period.physical_quantity
```

La apertura representa una **condición inicial del período**, no un movimiento físico adicional.

---

# 10. Variación de inventario

Una diferencia entre inventario teórico y físico no debe convertirse automáticamente en pérdida.

Ejemplo:

```text
Theoretical = 5
Physical    = 4

Variance = -1
```

El sistema debe registrar:

```text
Variance = -1
```

pero **no crear automáticamente**:

```text
LOSS = -1
```

La pérdida solamente debe registrarse cuando exista una operación explícita que la determine.

Esto permite distinguir:

```text
diferencia detectada
        ↓
investigación
        ↓
ajuste / pérdida / corrección
```

---

# 11. InventoryCount

Debe incorporarse un concepto genérico de conteo físico para permitir la auditoría tanto de Administrator/Replenisher como de Machine.

Conceptualmente:

```text
InventoryCount
- count_id
- location_id
- occurred_at
- actor_id
- status
```

y:

```text
InventoryCountLine
- product_id
- expected_quantity
- physical_quantity
- variance
```

El resultado de un conteo debe permitir determinar:

```text
expected
physical
variance
```

sin modificar automáticamente el ledger.

---

# 12. Replenishment Aggregate

`Replenishment` será un Aggregate Root.

```text
Replenishment
- replenishment_id
- machine_id
- replenisher_id
- started_at
- completed_at
- status
- location
- lines
```

Estados:

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

Una reposición completada o cancelada no puede modificarse.

---

# 13. ReplenishmentLine

Cada línea representa un movimiento físico de productos hacia o desde un slot.

```text
ReplenishmentLine
- line_id
- machine_position_id
- product_id
- quantity
- unit_price
- occurred_at
- product_description_snapshot
- preferred_product_id_snapshot
- replacement_reason
```

---

# 14. Signed Quantity

La cantidad de la línea será firmada.

```text
quantity > 0
    LOAD
    producto agregado al slot

quantity < 0
    UNLOAD
    producto retirado del slot

quantity = 0
    inválido
```

Ejemplo:

```text
+5 → cargar 5 unidades
-3 → retirar 3 unidades
 0 → inválido
```

---

# 15. Regla definitiva de capacidad

La capacidad limita **cada operación individual**, no el acumulado histórico del período.

Regla:

```text
0 < abs(quantity) <= capacity
```

Para capacidad `5`:

| Operación | Resultado |
| --------: | --------- |
|      `+1` | válida    |
|      `+5` | válida    |
|      `+6` | inválida  |
|      `-1` | válida    |
|      `-5` | válida    |
|      `-6` | inválida  |
|       `0` | inválida  |

No debe utilizarse:

```text
current_stock + quantity <= capacity
```

porque entre reposiciones pueden existir ventas que reduzcan el stock.

Por lo tanto:

```text
capacity = 5

+5
+5
+5
```

son tres operaciones válidas.

---

# 16. Product Substitution

`MachineSlot.preferred_product_id` representa una configuración/preferencia.

No representa necesariamente el producto realmente cargado.

Por lo tanto:

```text
MachineSlot
    preferred_product = Coca-Cola
```

puede recibir:

```text
ReplenishmentLine
    product = Sprite
```

si las reglas de sustitución lo permiten.

La sustitución debe conservar:

```text
preferred_product_id_snapshot
replacement_reason
```

Razones mínimas:

```text
OUT_OF_STOCK
SLOT_EMPTY
OPERATIONAL_DECISION
```

El producto preferido del slot **no debe modificarse automáticamente**.

---

# 17. Regla de precio

`MachineSlot.selling_price` representa la configuración actual.

`ReplenishmentLine.unit_price` representa el precio aplicado/histórico de esa operación.

No se debe reconstruir el precio histórico utilizando el precio actual del slot.

Una sustitución:

```text
preferred_product != actual_product
```

puede realizarse si:

```text
actual_price == configured_price
```

Una diferencia de precio debe rechazarse en este dominio mientras no exista una operación explícita de cambio de precio.

El precio no se utilizará para valorizar el inventario.

---

# 18. Snack Sales

Las ventas Snack no deben obligar a conocer el SKU vendido.

Conceptualmente:

```text
SnackSale
- machine_id
- slot_id
- quantity
- period
```

`product_id` puede ser desconocido.

Ejemplo:

```text
Opening       8
Coca-Cola    +5
Sprite       +3
Sales        -6
----------------
Slot total    10
```

El sistema puede conocer:

```text
cantidad total vendida = 6
```

pero no necesariamente:

```text
Coca-Cola vendidas = ?
Sprite vendidas    = ?
```

Por lo tanto, el dominio **no debe inventar una distribución por SKU**.

---

# 19. Coffee Sales

En máquinas Coffee, el consumo debe derivarse desde la selección y su receta.

Conceptualmente:

```text
CoffeeSale
- machine_id
- selection_id
- quantity
- occurred_at
```

La selección tiene una receta:

```text
Selection
    ↓
Recipe
    ↓
Ingredients / Containers
```

Ejemplo conceptual:

```text
Café
    → café

Cappuccino
    → café
    → leche

Mocaccino
    → café
    → leche
    → chocolate
```

Una venta:

```text
Mocaccino × 5
```

produce:

```text
café       ×5
leche      ×5
chocolate  ×5
```

según la receta configurada.

Si no existe receta válida, la operación debe rechazarse.

Si no existe inventario suficiente para efectuar el consumo conocido, la operación debe rechazarse.

---

# 20. Separación entre Sale e InventoryMovement

Una venta no debe convertirse universalmente en un `InventoryMovement` de producto.

El flujo correcto es:

```text
Sale
  ↓
Consumption calculation
  ↓
Inventory effects
```

Para Snack:

```text
SnackSale
    ↓
slot consumption
```

Para Coffee:

```text
CoffeeSale
    ↓
Selection
    ↓
Recipe
    ↓
Ingredient consumption
```

Esto evita imponer un modelo de inventario incorrecto sobre máquinas con comportamientos diferentes.

---

# 21. Casos de uso

Implementar los casos de uso de aplicación necesarios para expresar las operaciones del dominio.

Como mínimo:

```text
CreateReplenishment
AddReplenishmentLine
CompleteReplenishment
CancelReplenishment

RegisterInventoryMovement

CreateInventoryCount
RecordInventoryCountLine
CompleteInventoryCount

RegisterSnackSale
RegisterCoffeeSale
```

Los nombres concretos pueden adaptarse a las convenciones existentes del proyecto.

Los casos de uso deben delegar las reglas de negocio al dominio y no duplicarlas innecesariamente en la capa de aplicación.

---

# 22. Integración con Platform

Este commit **no implementa todavía la integración definitiva con la base de `nexo-platform`**.

Sin embargo, debe dejar claramente identificados los puntos que posteriormente necesitarán integración:

```text
Platform
    ↓
tenant/context
    ↓
repositories / persistence
    ↓
Vending domain
```

Antes de implementar:

* PostgreSQL.
* SQLAlchemy.
* repositorios concretos.
* Unit of Work definitivo.
* integración transaccional.

se debe revisar cómo la plataforma actual expone:

```text
Database
Session
UnitOfWork
RequestContext
tenant context
```

y determinar cuál es la forma correcta de consumirlos desde Vending sin romper la separación de capas.

---

# 23. Tests del Commit 6

El foco de testing será **unitario y de dominio**.

No se requiere PostgreSQL/Testcontainers en este commit.

### Replenishment

* REP-01 crear reposición.
* REP-02 agregar línea positiva.
* REP-03 agregar línea negativa.
* REP-04 rechazar cantidad cero.
* REP-05 completar reposición.
* REP-06 cancelar reposición.
* REP-07 impedir modificación después de completar.
* REP-08 impedir modificación después de cancelar.

### Capacidad

* CAP-01 capacidad 5, cantidad +5 válida.
* CAP-02 capacidad 5, cantidad +6 inválida.
* CAP-03 capacidad 5, cantidad -5 válida.
* CAP-04 capacidad 5, cantidad -6 inválida.
* CAP-05 cantidad 0 inválida.
* CAP-06 múltiples operaciones +5 válidas independientemente.

### Sustitución

* SUB-01 sustitución con mismo precio válida.
* SUB-02 sustitución con precio diferente rechazada.
* SUB-03 producto preferido permanece sin cambios.
* SUB-04 snapshot del producto preferido preservado.
* SUB-05 motivo de sustitución preservado.

### Inventory

* INV-01 assignment.
* INV-02 replenishment.
* INV-03 slot removal.
* INV-04 return.
* INV-05 adjustment.
* INV-06 loss.
* INV-07 cálculo de balance esperado.
* INV-08 `SLOT_REMOVAL` no se interpreta como `LOSS`.

### Machine Inventory

* MI-01 período inicial con opening = 0.
* MI-02 no se genera movimiento artificial de apertura.
* MI-03 replenishment positivo.
* MI-04 replenishment negativo.
* MI-05 consumo.
* MI-06 cálculo de inventario teórico.
* MI-07 physical count.
* MI-08 cálculo de variance.
* MI-09 variance no genera LOSS automáticamente.
* MI-10 siguiente período utiliza physical como opening.
* MI-11 cambio de capacidad no genera LOSS.

### Snack

* SNK-01 registrar venta por slot.
* SNK-02 permitir `product_id` desconocido.
* SNK-03 no inferir SKU vendido.
* SNK-04 sustituciones no modifican ventas históricas.
* SNK-05 calcular consumo total del slot.

### Coffee

* COF-01 consumo de receta de un ingrediente.
* COF-02 receta con dos ingredientes.
* COF-03 receta con tres ingredientes.
* COF-04 escalar consumo según cantidad vendida.
* COF-05 rechazar selección sin receta.
* COF-06 rechazar consumo insuficiente.
* COF-07 una venta produce múltiples consumos.

### Custody

* CUST-01 cálculo de inventario esperado de Administrator.
* CUST-02 cálculo de inventario esperado de Replenisher.
* CUST-03 conteo físico de Administrator.
* CUST-04 conteo físico de Replenisher.
* CUST-05 variance no genera LOSS.
* CUST-06 pérdida explícita genera movimiento LOSS.
* CUST-07 transferencia entre custodias conserva la cantidad total.

---

# 24. Documentación

Actualizar/crear:

```text
docs/architecture/INVENTORY_AND_REPLENISHMENT.md

docs/domain/INVENTORY_RULES.md
docs/domain/REPLENISHMENT_RULES.md
docs/domain/MACHINE_INVENTORY.md
docs/domain/SALES_AND_CONSUMPTION.md
docs/domain/INVENTORY_CUSTODY_AND_RECONCILIATION.md
```

ADRs:

```text
docs/adr/016-inventory-ledger.md
docs/adr/017-replenishment-as-aggregate.md
docs/adr/018-product-substitution.md
docs/adr/019-replenishment-pricing.md
docs/adr/021-machine-inventory-periods.md
docs/adr/022-snack-sales-without-product-attribution.md
docs/adr/023-coffee-sales-and-recipe-consumption.md
docs/adr/024-replenishment-capacity-rule.md
docs/adr/025-inventory-custody-and-reconciliation.md
```

La documentación debe dejar explícitamente separadas estas tres situaciones:

```text
Administrator / Replenisher
        ↓
inventario esperado instantáneo
        ↓
conteo físico
        ↓
variance
```

y:

```text
Machine
        ↓
opening
        ↓
replenishments
        ↓
consumption
        ↓
theoretical
        ↓
physical count
        ↓
variance
        ↓
next opening
```

---

# 25. Criterios de aceptación

El Commit 6 se considera terminado cuando:

1. Existe un modelo de dominio coherente para inventario y custodia.
2. `Replenishment` funciona como Aggregate Root.
3. Las líneas permiten cantidades positivas y negativas.
4. `quantity = 0` es inválido.
5. Se cumple:

```text
0 < abs(quantity) <= capacity
```

6. Las operaciones repetidas pueden superar acumulativamente la capacidad.
7. La sustitución de producto conserva el producto preferido.
8. Se preserva el snapshot histórico de la configuración.
9. El precio histórico pertenece a la línea de reposición.
10. Existe `InventoryMovement`.
11. `SLOT_REMOVAL` se distingue de `LOSS`.
12. Administrator tiene inventario esperado calculable.
13. Replenisher tiene inventario esperado calculable.
14. Machine tiene inventario teórico por período.
15. El opening inicial es cero.
16. No existe movimiento artificial `OPENING_BALANCE`.
17. El physical count permite calcular variance.
18. Una variance no genera automáticamente LOSS.
19. El siguiente período de máquina utiliza el physical count anterior como opening.
20. Snack permite ventas sin atribución obligatoria a SKU.
21. Coffee utiliza recetas para determinar consumo.
22. Una venta Coffee puede generar múltiples consumos.
23. Las reglas están encapsuladas en el dominio.
24. El dominio no depende de PostgreSQL, SQLAlchemy, FastAPI ni `nexo-platform`.
25. Los casos de uso principales están cubiertos por tests unitarios.
26. No se implementa todavía persistencia ni integración definitiva con la base de Platform.
27. La arquitectura queda preparada para realizar esa integración en el siguiente commit.

---

# 26. Definition of Done

```text
[ ] Domain entities implemented
[ ] Value objects implemented where appropriate
[ ] Replenishment aggregate implemented
[ ] ReplenishmentLine implemented
[ ] Signed quantity implemented
[ ] Capacity rule implemented
[ ] Product substitution implemented
[ ] Historical price implemented
[ ] InventoryMovement implemented
[ ] Inventory custody model implemented
[ ] Administrator expected inventory implemented
[ ] Replenisher expected inventory implemented
[ ] MachineInventoryPeriod implemented
[ ] InventoryCount implemented
[ ] Variance calculation implemented
[ ] Snack consumption implemented
[ ] Coffee recipe consumption implemented
[ ] Application use cases implemented
[ ] Unit tests implemented
[ ] Domain dependency boundaries verified
[ ] Documentation updated
[ ] ADRs updated

[ ] PostgreSQL integration NOT implemented
[ ] Platform DB integration NOT implemented
[ ] Idempotency NOT implemented
[ ] Concurrency NOT implemented
[ ] Multi-tenancy infrastructure NOT implemented
[ ] HTTP API NOT implemented
```

---

# 27. Resultado arquitectónico esperado

Al finalizar este commit, la arquitectura conceptual debe quedar:

```text
                    VENDING DOMAIN
                         │
        ┌────────────────┼─────────────────┐
        │                │                 │
   Replenishment     Inventory          Sales
        │                │                 │
        │          ┌─────┴─────┐      ┌────┴─────┐
        │          │           │      │          │
        │     Administrator Replenisher Snack   Coffee
        │                                │       │
        │                                │     Recipe
        │                                │       │
        └───────────────┐                │    Consumption
                        │                │
                     Machine ────────────┘
                        │
                 Inventory Period
                        │
                  Physical Count
                        │
                     Variance
```

El resultado de este commit **no debe intentar resolver todavía cómo se persiste este modelo**.

El siguiente paso natural será revisar la infraestructura existente de `nexo-platform` y determinar:

```text
¿Cómo consume Vending la base de datos de Platform?
¿Qué Session/UnitOfWork existe?
¿Cómo se resuelve el contexto?
¿Dónde viven los repositorios?
¿Cómo se implementa la transacción?
¿Cómo se modelan los límites de tenant?
```

Solo después de esa revisión conviene definir el siguiente commit de **persistencia e integración**, evitando diseñar una segunda infraestructura paralela dentro de Vending.
