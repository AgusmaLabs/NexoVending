# Dependency Rules — NexoVending

## External

```text
nexo_vending ──► nexo_platform   (public API only; Application/API layers)
nexo_platform ─✕─► nexo_vending
```

## Internal layers

```text
api            ──► application
application    ──► domain (ports / entities)
infrastructure ──► domain ports
domain         ─✕─► api | infrastructure | fastapi | sqlalchemy | nexo_platform
```

## Domain modules

Allowed conceptual dependencies:

```text
replenishment ──► machines, common
inventory     ──► common
machines      ──► common
products      ──► common
identity      ──► common
```

Forbidden:

```text
products ─✕─► replenishment
domain   ─✕─► nexo_platform.RequestContext
```

## Tenant isolation

```text
RequestContext.tenant_id  (Platform)
        │
        ▼
   Application
        │
        ▼
 Repository queries (scoped by authenticated tenant)
```

Never:

```text
WHERE tenant_id = <client payload>
```

## Concurrency (inventory)

Domain defines available quantity and rejects negative stock.

Lost-update prevention under concurrent consumptions is a **persistence** concern (locking / optimistic version) and must not be “solved” only with in-process Python assumptions.
