# Operator Access Model

## Matrix (V3)

| Condition | Replenish |
| --- | ---: |
| PENDING | ❌ |
| ACTIVE + OPERATOR + within validity | ✅ |
| ACTIVE + OPERATOR + expired / not yet valid | ❌ |
| SUSPENDED | ❌ |
| DISABLED | ❌ |
| ACTIVE + ADMIN | administrative policy (not replenish by default) |

Validity interval is half-open: `[valid_from, valid_until)`.

## Ownership

| Concern | Owner |
| --- | --- |
| Authentication | Platform (`nexo-platform==1.11.0`) |
| Identity binding (Principal → Operator) | Vending |
| Authorization (status/role/validity) | Vending |
| Tenant authority | Platform `RequestContext` |

## Security rules

- Never trust `tenant_id` or `operator_id` from client payload as authority.
- Resolve operator with `context.tenant_id` + `context.principal`.
- Do not branch business logic on `provider == "google"`.
