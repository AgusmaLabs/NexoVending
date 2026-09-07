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

## Objetivo V01

Bootstrap de producto:

- paquete `nexo_vending` / distribución `nexo-vending`;
- FastAPI con `/health` y `/health/ready`;
- PostgreSQL + Alembic propios;
- integración con la API pública de Platform (`Tenant`, `UnitOfWork`, `DomainEvent`, `RequestContext`);
- architecture tests, Testcontainers, clean-install y Docker smoke.

**Todavía no** incluye dominio de máquinas, productos, inventario ni reposición (eso es V02+).

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
| [MIGRATIONS.md](MIGRATIONS.md) | Migraciones separadas |
| [docs/adr/ADR-001-vending-product-boundary.md](docs/adr/ADR-001-vending-product-boundary.md) | Decisión de producto independiente |

## Agent Core

V01 **no** depende de `nexo-agent-core`. Primero se valida Vending → Platform.
