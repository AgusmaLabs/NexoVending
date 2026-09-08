# ADR-006: Platform authentication ownership

- Status: Accepted
- Date: 2026-09-08

## Context

Vending needs authenticated operators (initially via Google) without owning OAuth/JWT infrastructure.

## Decision

All transversal authentication belongs to `nexo-platform==1.2.0`.

Vending consumes:

- `AuthenticationProvider`
- `AuthenticationResult`
- `AuthenticatedIdentity`
- `ExternalIdentity`
- `Principal`
- `RequestContext`

Vending does not implement OAuth providers, Google clients, or JWT.

## Consequences

- Authentication upgrades land in Platform once.
- Vending remains provider-agnostic at the business layer.
- Architecture tests forbid local oauth/jwt/google modules in Vending.

## Alternatives considered

1. Implement Google OAuth inside Vending — rejected; duplicates Platform and couples product to provider.
2. Copy Platform identity modules — rejected; breaks package boundary.
