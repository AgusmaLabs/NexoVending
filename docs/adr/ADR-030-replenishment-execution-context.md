# ADR-030: Replenishment execution context and machine access

- Status: Accepted
- Date: 2026-09-11

## Context

V9 exposed replenishment HTTP endpoints. Mobile clients still needed a formal execution context: machine identification (QR), replenisher↔machine authorization, operational slots, barcode lookup, and GPS capture without embedding business rules in Flutter.

## Decision

1. **Machine** is the operational aggregate for replenishment execution.
2. **QR / codes** are `MachineIdentifier` capture mechanisms — no QR libraries in Domain.
3. **Tenant** authority comes only from Platform `RequestContext`.
4. **MachineAssignment** + `MachineAccessPolicy` authorize replenishers (validity window + ACTIVE machine/operator).
5. **Location** is captured on start (`GeoLocation`); GPS ≠ geofencing in V10.
6. **Barcode lookup** queries the catalog and never auto-creates products.
7. **Add line** validates slot ownership, capacity, replenisher inventory, and product existence inside Platform UoW.
8. Transaction / Idempotency / Observability remain Platform capabilities.

## Consequences

- Migration `0003_machine_assignments`.
- Endpoints: `/machines/resolve`, `/machines/{id}`, `/machines/{id}/slots`, `/products/barcode/{barcode}`.
- Start replenishment requires an effective assignment.

## Alternatives considered

1. Role-only access without assignment — rejected (too coarse).
2. Geofencing in V10 — deferred (`MachineLocationPolicy` later).
3. Auto-create products from unknown barcodes — rejected.
