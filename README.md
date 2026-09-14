# NexoVending

Producto de negocio para operar máquinas vending. Consume **nexo-platform** como dependencia externa instalable — no como carpeta hermana en el mismo árbol de código.

## Relación con Platform

```text
nexo-vending
      │
      ├──────────────→ nexo-platform   (pip: nexo-platform==1.11.0)
      │
      └──────────────→ PostgreSQL      (schema propio de Vending)
```

NexoPlatform **no** depende de NexoVending.

## Objetivo V01 / V02

**V01** — bootstrap de producto (paquete, health, Postgres/Alembic, Docker, CI, Platform dependency).

**V02** — domain foundation (Product, Machine, Inventory ledger, Replenishment aggregate, ports, use cases in-memory).

**V03** — tenant-scoped Operator identity & authorization on Platform auth (`nexo-platform==1.10.0`).

**V04** — tenant-scoped Product catalog (barcode, lifecycle, lookup).

**V05** — Machine & physical slot configuration (SNACK/COFFEE/MIXED, capacity, preferred product, selling price).

**V06** — Inventory custody ledger, replenishment signed lines, machine periods, snack/coffee consumption (domain).

**Todavía no** incluye persistencia de dominio, API REST de negocio ni scanner hardware.

## Requisitos

- Python 3.12+
- Docker (para Compose / Testcontainers)
- Acceso al repositorio/wheel de `nexo-platform==1.11.0` (aún no publicado en PyPI público)

## Instalación (desarrollo)

```bash
# 1) Generar wheel de Platform en ./vendor
python scripts/vendor_platform.py
# o: python scripts/vendor_platform.py --platform-root /ruta/a/NexoPlatform

# 2) Instalar Vending (pip resuelve nexo-platform desde vendor/)
pip install -e ".[dev]" --find-links=vendor
```

## Ejecutar API

```bash
# Con Compose (API + PostgreSQL)
docker compose up --build

# O localmente (requiere DATABASE_URL apuntando a Postgres)
alembic upgrade head
uvicorn nexo_vending.main:app --reload
```

Endpoints:

- `GET /health` → `status`, `package_version`, `api_version`
- `GET /health/ready` → readiness + same version fields (valida PostgreSQL)
- Business API under `/api/v1/...` (see [docs/api/MOBILE_API_CONTRACT.md](docs/api/MOBILE_API_CONTRACT.md))
- Versioning policy: [docs/VERSIONING.md](docs/VERSIONING.md)

```bash
# Export OpenAPI for frontend codegen
python scripts/export_openapi.py --out docs/api/openapi-v1.json
```

## Tests

```bash
# Unit + architecture + integration (incluye Testcontainers)
pytest -q

# Clean-install del wheel
pytest tests/packaging -q -m packaging

# Docker smoke
pytest tests/e2e -q -m e2e
```

## Documentación

| Documento | Contenido |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Límites Vending ↔ Platform |
| [docs/architecture/DOMAIN.md](docs/architecture/DOMAIN.md) | Mapa e invariantes de dominio |
| [docs/architecture/DEPENDENCIES.md](docs/architecture/DEPENDENCIES.md) | Reglas de dependencia |
| [docs/VERSIONING.md](docs/VERSIONING.md) | SemVer del paquete + versionado HTTP `/api/v1` |
| [docs/api/MOBILE_API_CONTRACT.md](docs/api/MOBILE_API_CONTRACT.md) | Contrato HTTP para Flutter / mobile |
| [MIGRATIONS.md](MIGRATIONS.md) | Migraciones separadas |
| [docs/architecture/IDENTITY_BOUNDARY.md](docs/architecture/IDENTITY_BOUNDARY.md) | Auth Platform vs Operator Vending |
| [docs/architecture/PRODUCT_CATALOG.md](docs/architecture/PRODUCT_CATALOG.md) | Catálogo de productos |
| [docs/domain/PRODUCT_CATALOG_RULES.md](docs/domain/PRODUCT_CATALOG_RULES.md) | Reglas del catálogo |
| [docs/adr/](docs/adr/) | ADRs (producto, monolito, ledger, aggregate, tenant, auth, operator, catalog) |

## Agent Core

V01 **no** depende de `nexo-agent-core`. Primero se valida Vending → Platform.
