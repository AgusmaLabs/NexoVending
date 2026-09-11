# Machines HTTP API

API prefix: `/api/v1` (see [VERSIONING.md](../VERSIONING.md)).

| Method | Path | Permission |
| --- | --- | --- |
| GET | `/machines/resolve?identifier_type=&value=` | `machine.resolve` |
| GET | `/machines/{machine_id}` | `machine.read` |
| GET | `/machines/{machine_id}/slots` | `machine.read` |

`identifier_type`: `INTERNAL_ID` | `QR_CODE` (QR maps to tenant-scoped `MachineCode`).

Requires entitlement `vending.replenishment` and an effective machine assignment.
