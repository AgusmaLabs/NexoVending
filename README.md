# NexoVending

Producto de negocio para operar máquinas vending. Consume **nexo-platform** como dependencia externa instalable — no como carpeta hermana en el mismo árbol de código.

## Relación con Platform

```text
nexo-vending
      │
      ├──────────────→ nexo-platform   (pip: nexo-platform==1.0.0)
      │
      └──────────────→ PostgreSQL      (schema propio de Vending)
```

NexoPlatform **no** depende de NexoVending.

## Objetivo V01 / V02

**V01** — bootstrap de producto (paquete, health, Postgres/Alembic, Docker, CI, Platform dependency).

**V02** — domain foundation (Product, Machine, Inventory ledger, Replenishment aggregate, ports, use cases in-memory).

**Todavía no** incluye persistencia de dominio, API de negocio, Google OAuth ni apps móviles.

## Requisitos

- Python 3.12+
- Docker (para Compose / Testcontainers)
- Acceso al repositorio/wheel de `nexo-platform==1.0.0` (aún no publicado en PyPI público)

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

- `GET /health` → `{"status":"ok"}`
- `GET /health/ready` → `{"status":"ready"}` (valida PostgreSQL)

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
| [docs/api/DOMAIN_CONTRACTS.md](docs/api/DOMAIN_CONTRACTS.md) | Contratos de aplicación/dominio |
| [MIGRATIONS.md](MIGRATIONS.md) | Migraciones separadas |
| [docs/adr/](docs/adr/) | ADRs (producto, monolito, ledger, aggregate, tenant) |

## Agent Core

V01 **no** depende de `nexo-agent-core`. Primero se valida Vending → Platform.
