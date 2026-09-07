# Migrations — NexoVending

## Separation

```text
nexo-platform
    migrations/
        Platform schema (tenants, identity, billing, outbox, …)

nexo-vending
    migrations/
        Vending schema (machines, products, inventory, … — future)
```

These chains are **independent**.

- Vending never modifies Platform migrations.
- Platform never owns Vending tables.
- Each product has its own `DATABASE_URL` / database (or schema ownership) and Alembic history.

## V01 state

Current revision:

```text
migrations/versions/0001_vending_bootstrap.py
```

It is intentionally a no-op (no domain tables yet). It exists so that:

```bash
alembic upgrade head
alembic downgrade base
```

are validated against real PostgreSQL from day one.

## Commands

```bash
# Apply
alembic upgrade head

# Roll back
alembic downgrade -1

# New revision (when domain tables appear)
alembic revision -m "add_machines"
```

`DATABASE_URL` is read from the environment / `nexo_vending.config.Settings`.
