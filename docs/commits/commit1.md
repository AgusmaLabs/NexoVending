El objetivo es demostrar que tenemos un producto independiente que consume nexo-platform como una dependencia externa.

V01 — Bootstrap Vending Product + Platform Integration
Commit
feat(vending): bootstrap vending product with platform integration
Objetivo

Crear el nuevo repositorio:

nexo-vending/

capaz de:

instalar y consumir nexo-platform;
arrancar como aplicación independiente;
conectarse a PostgreSQL;
tener sus propias migraciones;
respetar Tenant/RequestContext de Platform;
tener boundaries arquitectónicos desde el primer día;
ejecutarse en Docker;
tener CI;
demostrar mediante tests que Vending depende de Platform, pero Platform no depende de Vending.

El resultado debe ser:

nexo-vending
      │
      ├──────────────→ nexo-platform
      │
      └──────────────→ PostgreSQL

y no:

nexo-vending
      │
      └── copia de código de nexo-platform ❌
1. Estructura inicial

Propongo arrancar con:

nexo-vending/
│
├── src/
│   └── nexo_vending/
│       ├── api/
│       │   ├── health.py
│       │   └── router.py
│       │
│       ├── application/
│       │   └── ...
│       │
│       ├── domain/
│       │   └── ...
│       │
│       ├── infrastructure/
│       │   └── ...
│       │
│       ├── config.py
│       └── main.py
│
├── migrations/
│   └── versions/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── architecture/
│   └── e2e/
│
├── docs/
│   └── adr/
│
├── ARCHITECTURE.md
├── README.md
├── MIGRATIONS.md
├── pyproject.toml
├── alembic.ini
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── .gitignore
└── .github/
    └── workflows/
        └── ci.yml

No volvería a utilizar:

src/modules/
src/platform/
src/platform_core/
src/products/

Ese fue precisamente el problema que estamos corrigiendo.

2. Dependencia real de Platform

El pyproject.toml debe declarar:

dependencies = [
    "nexo-platform==1.x.x",
]

La versión debe ser la versión realmente publicada de P22.

No:

"../nexo-platform"

No:

"nexo-platform @ file://..."

No git submodule.

No copiar código.

Esto es fundamental porque queremos validar desde el primer commit el modelo:

external package
       ↓
nexo-vending
3. Primer consumidor real de la Public API

V01 debe utilizar exclusivamente la API pública de Platform.

Por ejemplo:

from nexo_platform import (
    DomainEvent,
    Tenant,
    UnitOfWork,
)

No permitiría:

from nexo_platform.infrastructure...
from nexo_platform.persistence...
from nexo_platform.modules...

salvo que alguno de esos módulos haya sido definido explícitamente como API pública.

La regla es:

Vending conoce contratos públicos de Platform, no su implementación.

4. Tenant integration

Este commit debe demostrar que Vending puede operar dentro de un Tenant.

Por ejemplo, conceptualmente:

Request
   │
   ▼
Tenant Context
   │
   ▼
Vending Application
   │
   ▼
Platform

Pero V01 no debe crear todavía una entidad Vending asociada a Tenant.

Solo necesitamos probar que podemos obtener/propagar el contexto.

Por ejemplo:

tenant_id = request_context.tenant_id

según el contrato real que haya quedado definido en P22.

5. Health endpoint

Crear:

GET /health

con una respuesta mínima:

{
  "status": "ok"
}

Y otro endpoint recomendable:

GET /health/ready

para readiness.

Por ejemplo:

{
  "status": "ready"
}

El segundo debería comprobar PostgreSQL cuando corresponda.

6. No crear todavía dominio Vending

Esto es intencional.

No agregaría en V01:

Machine
Product
Slot
Inventory
Replenishment
Route
Operator

El objetivo es validar infraestructura y boundaries.

El siguiente commit será el momento correcto para empezar:

V02 → Machine + MachineSlot

o, dependiendo de cómo queramos estructurar el dominio:

V02 → Vending Domain Foundation
7. PostgreSQL propio de Vending

Vending debe tener su propia configuración:

DATABASE_URL

y su propia infraestructura SQLAlchemy.

Por ejemplo:

nexo-vending
      │
      ▼
PostgreSQL
      │
      └── vending database

No debe importar los modelos ORM de Platform.

Esto significa que Platform puede tener:

Tenant
Subscription
Invoice
Charge
Outbox

mientras Vending tendrá posteriormente:

Machine
Product
Slot
Inventory
Replenishment
8. Migrations separadas

V01 debe crear su propio Alembic.

nexo-vending/
└── migrations/
    └── versions/

Y debe quedar explícitamente documentado:

Platform migrations
        ≠
Vending migrations

Inicialmente podemos tener:

migrations/
└── versions/
    └── 0001_vending_bootstrap.py

pero incluso puede ser una migration vacía/no-op si todavía no existen tablas de dominio.

Personalmente prefiero no crear tablas artificiales solo para tener una migration.

Podemos tener el directorio y validar Alembic con upgrade head.

9. No duplicar Outbox

Esto es importante.

Vending no debe crear:

nexo_vending/outbox/

para duplicar el mecanismo de Platform.

Cuando llegue el momento de emitir:

ReplenishmentCreated

la infraestructura utilizará el contrato de Platform.

Conceptualmente:

Vending Domain
     │
     ▼
DomainEvent
     │
     ▼
nexo-platform
     │
     ▼
Outbox

No:

Vending
   └── VendingOutbox ❌
10. No duplicar UnitOfWork

Mismo principio.

Vending no implementará:

VendingUnitOfWork

si el contrato de Platform ya resuelve la unidad transaccional.

La aplicación Vending podrá consumir:

from nexo_platform import UnitOfWork

y utilizarlo en sus casos de uso.

11. Configuration

Crear:

src/nexo_vending/config.py

con configuración específica de producto.

Por ejemplo:

APP_NAME
APP_ENV
DATABASE_URL
API_PREFIX
LOG_LEVEL

Pero evitar copiar la configuración de Platform.

La separación debe ser:

Platform configuration
        │
        └── Platform concerns

Vending configuration
        │
        └── Vending concerns
12. FastAPI

V01 puede utilizar FastAPI como shell de aplicación:

main.py
   │
   ▼
FastAPI
   │
   ├── /health
   └── /health/ready

No necesitamos endpoints de negocio todavía.

El objetivo es poder ejecutar:

uvicorn nexo_vending.main:app
13. Docker

Docker debe instalar el proyecto como paquete:

RUN pip install .

y no depender de:

PYTHONPATH=/app/src

como mecanismo para que funcione.

El objetivo es:

Docker
   ↓
pip install nexo-vending
   ↓
pip install nexo-platform
   ↓
run application
14. Docker Compose

Para desarrollo:

docker-compose
│
├── vending-api
│
└── postgres

La aplicación debe conectarse mediante:

DATABASE_URL

No hardcodear:

localhost

ni credenciales.

15. Architecture rules

Desde V01 pondría architecture tests.

Permitido
nexo_vending
       ↓
nexo_platform
Prohibido
nexo_platform
       ↓
nexo_vending

Aunque actualmente Platform esté en otro repositorio, el test debe establecer la regla conceptual.

16. Domain boundary

Aunque todavía no tengamos entidades, debemos establecer:

nexo_vending.domain

no puede importar:

fastapi
sqlalchemy

ni infraestructura.

Regla:

domain
   ↓
application/contracts
   ↓
infrastructure

y:

api
   ↓
application

No:

domain
   ↓
FastAPI ❌
17. Test suite

Yo dividiría los tests así.

Unit
tests/unit/

Tests de:

configuración;
composición de aplicación;
health logic si existe lógica;
errores básicos.
18. Package integration test
tests/integration/test_platform_dependency.py

Debe demostrar que:

import nexo_platform
import nexo_vending

funcionan simultáneamente.

Y que Vending puede utilizar, por ejemplo:

from nexo_platform import DomainEvent

sin importar internals.

19. Clean-install test

Este es obligatorio.

El CI debe:

build nexo-vending
       ↓
crear entorno limpio
       ↓
instalar wheel
       ↓
instalar nexo-platform
       ↓
import nexo_vending
       ↓
ejecutar smoke test

Queremos demostrar:

Vending funciona como consumidor de paquetes, no como carpeta hermana del repositorio Platform.

20. PostgreSQL/Testcontainers

Crear:

tests/integration/test_postgres.py

que levante PostgreSQL real.

Debe validar:

nexo-vending
       ↓
SQLAlchemy
       ↓
PostgreSQL real

No usar SQLite para reemplazar PostgreSQL en esta prueba.

21. Alembic integration test

Test:

tests/integration/test_migrations.py

Flujo:

PostgreSQL
    ↓
alembic upgrade head
    ↓
success
    ↓
alembic downgrade
    ↓
success

Aunque todavía no existan tablas de dominio complejas.

Esto deja preparado el mecanismo antes de empezar a crear entidades.

22. Docker smoke test

Este test debe ejecutarse en CI o como validación explícita:

docker compose build
docker compose up -d

Luego:

curl /health

y:

curl /health/ready

Debe responder correctamente.

23. Test de ausencia de código copiado

Pondría una regla muy interesante:

El repositorio Vending no debe contener:

nexo_platform/
src/platform/
src/platform_core/
modules/billing/
modules/tenant/
modules/identity/

Esto evita que alguien resuelva una necesidad copiando Platform.

24. Test de dependency leakage

Vending puede:

from nexo_platform import Tenant

pero no:

from nexo_platform.persistence.sqlalchemy import ...

si eso no es API pública.

Esto protege el desacoplamiento desde el principio.

25. Test de Tenant isolation contract

Aunque todavía no tengamos entidades Vending, podemos establecer el contrato:

Tenant A
   ↓
Vending request

Tenant B
   ↓
Vending request

y comprobar que el contexto de tenant no se mezcla.

No necesitamos todavía hacer queries de máquinas.

El objetivo es probar el boundary contract, no el dominio.

26. CI

El pipeline de V01 debería quedar:

                    ┌──────────┐
                    │   Ruff   │
                    └────┬─────┘
                         ↓
                    ┌──────────┐
                    │  Pytest  │
                    └────┬─────┘
                         ↓
                ┌─────────────────┐
                │ Architecture    │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Build wheel     │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Clean install   │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Testcontainers  │
                └────────┬────────┘
                         ↓
                ┌─────────────────┐
                │ Docker smoke    │
                └─────────────────┘
27. Documentación

V01 debería generar cuatro documentos.

README.md

Debe explicar:

qué es NexoVending;
objetivo de V1;
relación con Platform;
instalación;
desarrollo;
Docker;
tests.
ARCHITECTURE.md

Debe mostrar:

             nexo-platform
                   ▲
                   │
                   │ dependency
                   │
             nexo-vending
                   │
          ┌────────┼────────┐
          ▼        ▼        ▼
       Machine   Product  Inventory

aunque las entidades todavía no existan.

docs/adr/ADR-001-vending-product-boundary.md

Debe definir:

Vending como producto independiente;
dependencia de Platform;
ausencia de dependencia inversa;
ownership de datos;
migrations;
transaction boundary;
API boundary;
future Agent Core integration.
MIGRATIONS.md

Debe establecer:

nexo-platform
    migrations/
        Platform schema

nexo-vending
    migrations/
        Vending schema

y explicar que Vending no modifica las migrations de Platform.

28. Agent Core

En V01 no agregaría nexo-agent-core como dependencia.

Esto es deliberado.

Primero queremos demostrar:

nexo-vending
       ↓
nexo-platform

Después:

nexo-vending
       ↓
nexo-agent-core
       ↓
nexo-platform

Así podemos saber exactamente qué aporta cada capa.

29. Criterios de aceptación

Yo dejaría V01 aprobado solo si:

Repository
 Existe repo independiente nexo-vending.
 No contiene código copiado de Platform.
 No contiene src/platform.
 No contiene platform_core.
 No contiene products/vending heredado.
Package
 Python package = nexo_vending.
 Distribution = nexo-vending.
 pip install . funciona.
 nexo-platform se instala como dependencia.
 No existe dependencia local al repo Platform.
Platform integration
 Vending importa Platform únicamente mediante API pública.
 Tenant context puede propagarse.
 UnitOfWork puede consumirse.
 DomainEvent puede consumirse.
 No se duplican Outbox/transaction primitives.
Database
 PostgreSQL real funciona.
 Alembic funciona.
 Migrations de Vending están separadas.
 No se modifican migrations de Platform.
API
 /health funciona.
 /health/ready funciona.
 Readiness valida dependencias necesarias.
Architecture
 Vending → Platform permitido.
 Platform → Vending prohibido.
 Domain no importa infrastructure.
 Domain no importa FastAPI.
 No existen imports internos no permitidos de Platform.
Docker
 Docker build funciona.
 Docker Compose levanta API + PostgreSQL.
 /health funciona dentro del contenedor.
 /health/ready funciona con PostgreSQL.
CI
 Ruff pasa.
 Unit tests pasan.
 Integration tests pasan.
 Architecture tests pasan.
 Testcontainers pasa.
 Clean-install test pasa.
 Docker smoke test pasa.
30. Definition of Done

El criterio que usaría para cerrar V01 es este:

NexoVending debe poder ejecutarse desde un entorno limpio, instalando nexo-vending y obteniendo nexo-platform como dependencia externa, sin copiar ni importar internals de Platform, conectándose a PostgreSQL y pasando sus architecture/integration tests.

Eso demuestra que ya tenemos:

             PACKAGE
                │
                ▼
        ┌───────────────┐
        │ nexo-platform │
        └───────┬───────┘
                │
                │ pip dependency
                ▼
        ┌───────────────┐
        │ nexo-vending  │
        └───────┬───────┘
                │
                ▼
           PostgreSQL

y no simplemente dos carpetas que funcionan porque están dentro del mismo proyecto.