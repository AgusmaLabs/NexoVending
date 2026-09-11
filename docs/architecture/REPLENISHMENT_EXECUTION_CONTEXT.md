# Replenishment execution context

Status: **Implemented** (V10).

```text
Replenisher
  → identify machine (INTERNAL_ID | QR_CODE)
  → MachineAccessPolicy + assignment
  → capture location + start replenishment
  → slots / barcode / add lines
  → complete
```

| Concern | Owner |
| --- | --- |
| Actor / tenant / request_id | Platform `RequestContext` |
| Machine identity | Vending `MachineIdentifier` |
| Machine access | `MachineAssignment` + `MachineAccessPolicy` |
| Location capture | `GeoLocation` on start (no geofencing yet) |
| Line timestamps | `occurred_at` per line |
| Inventory availability | checked on add-line (load) |

Flutter captures data; Vending decides validity.

See [ADR-030](../adr/ADR-030-replenishment-execution-context.md), [MACHINE_ACCESS.md](MACHINE_ACCESS.md).
