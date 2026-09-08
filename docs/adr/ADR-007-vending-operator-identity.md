# ADR-007: Vending Operator identity

- Status: Accepted
- Date: 2026-09-08

## Context

Platform authentication yields a `Principal`. Vending needs tenant-scoped business operators with status, role, and validity.

## Decision

`Operator` is a Vending domain entity:

```text
Platform Principal + Vending Tenant → Operator
```

The same external principal may map to different operators per tenant. Lookup is always `tenant_id + principal.provider + principal.subject`.

Platform `User` is not used as the Vending operator model.

## Consequences

- Clear split between authentication identity and operational identity.
- Multi-tenant operator isolation is explicit.
- Persistence (later) must unique-index `(tenant_id, provider, subject)`.

## Alternatives considered

1. Reuse Platform User as Operator — rejected; mixes transversal account with vending rules.
2. Encode tenant inside Principal — rejected; tenant is request context, not identity issuer data.
