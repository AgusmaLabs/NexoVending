# ADR-002: Modular monolith for Vending

- Status: Accepted
- Date: 2026-09-07

## Context

Vending needs clear domain boundaries (products, machines, inventory, replenishment) without the operational cost of microservices at this stage.

## Decision

Implement NexoVending V2 as a **modular monolith**:

- one deployable (`nexo-vending`);
- explicit domain modules under `nexo_vending.domain.*`;
- hexagonal layers (`api` / `application` / `domain` / `infrastructure`);
- extraction to services remains possible later if a module’s scale demands it.

## Consequences

- Faster delivery and simpler Docker/VPS operations.
- Module dependency rules must be enforced with architecture tests.
- Shared database may come later per module ownership, still without premature service split.

## Alternatives considered

1. Microservices per domain module — rejected as premature.
2. Keep a single unstructured package — rejected; hides boundaries.
