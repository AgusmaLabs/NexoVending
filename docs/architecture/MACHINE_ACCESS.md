# Machine access

Status: **Implemented** (V10).

## Rules

1. `machine.tenant_id` must match `RequestContext.tenant_id`.
2. Machine must be `ACTIVE`.
3. Operator must be ACTIVE OPERATOR within validity (`can_operator_replenish`).
4. An **ACTIVE** `MachineAssignment` for `(tenant, replenisher, machine)` must be effective at the operation timestamp.
5. ADMIN cannot replenish by default (inventory/catalog admin path).

Assignments are provisioned via `AssignMachineToReplenisher` (admin).

GPS location on start does **not** authorize access.
