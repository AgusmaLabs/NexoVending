# Identity Boundary — NexoVending

## Separation

```text
Platform Authentication          Vending Identity / Authorization
───────────────────────          ────────────────────────────────
AuthenticationProvider           Operator
AuthenticationResult             OperatorRole / OperatorStatus
AuthenticatedIdentity            ValidityPeriod
ExternalIdentity                 can_operator_replenish()
Principal                        ResolveOperator / ProvisionOperator
RequestContext.tenant_id
RequestContext.principal
GoogleOAuthProvider / JWT
```

## Flow

```text
Google
  → nexo-platform 1.2.0 (AuthenticationResult / Principal)
  → RequestContext
  → nexo-vending ResolveOperator
  → Operator (tenant + principal)
  → status + role + validity
  → authorized / rejected
```

Forbidden:

```text
Google → nexo-vending Google OAuth
```

## Rules

- Domain identity may bind `nexo_platform.identity.authentication.Principal` only.
- Domain must not import Google / JWT / OAuth SDKs.
- Tenant and actor authority come from `RequestContext`, never from client payload.
- Platform `User` ≠ Vending `Operator`.
