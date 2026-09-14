# Mobile Authentication Contract — NexoVending

Status: **Implemented** (V12 monolito fachada + Platform `1.11.0` session JWT).  
Audience: Flutter / mobile developers, Platform auth owners, Vending maintainers.  
Related: [MOBILE_API_CONTRACT.md](MOBILE_API_CONTRACT.md), [IDENTITY_BOUNDARY.md](../architecture/IDENTITY_BOUNDARY.md), [ADR-006](../adr/ADR-006-platform-authentication.md), [ADR-029](../adr/ADR-029-vending-http-api-boundary.md), [ADR-033](../adr/ADR-033-monolith-session-facade.md), [OPERATOR_ACCESS_MODEL.md](../security/OPERATOR_ACCESS_MODEL.md).  
Platform pin: `nexo-platform==1.11.0`.

---

## 1. Purpose

1. How does Flutter obtain `Authorization: Bearer …`?
2. How does Flutter obtain tenant context?
3. Where do OAuth / Google Sign-In / JWT crypto live?

**Decision:** **Monolito fachada** — Flutter uses a single Vending host; Platform library owns crypto/OAuth; Vending owns Operator authorization.

---

## 2. Flow (Implemented)

```text
Flutter Google Sign-In → id_token
  → POST /api/v1/auth/session { id_token, tenant_id }
       → AuthenticationProvider.authenticate
       → ResolveOperator (must exist)
       → JwtService.issue_session(..., tenant_id=accepted)
       ← { access_token, token_type: Bearer, expires_in }
  → GET/POST /api/v1/...
       Authorization: Bearer <JWT>
       X-Tenant-Id: optional (must match claim if sent)
       → JwtService.decode_session
       → RequestContext → ResolveOperator → policies
```

`GET /api/v1/operators/me` returns the Vending Operator after auth (bootstrap).

---

## 3. Headers

| Credential | `Authorization` | `X-Tenant-Id` |
| --- | --- | --- |
| Session JWT (production / mobile) | `Bearer <jwt>` | Optional; must match `session.tenant_id` |
| Harness (tests/CI) | `Bearer principal/<provider>/<subject>` | **Required** |

Never send `tenant_id` / `operator_id` as authority on business JSON bodies. Body `tenant_id` is allowed **only** on `POST /auth/session` (product acceptance, verified against Operator).

---

## 4. Separation of responsibilities

| Layer | Owns |
| --- | --- |
| Flutter | Google Sign-In SDK → `id_token` |
| Vending HTTP | `/auth/session`, dual-credential `auth.py`, `/operators/me` |
| Platform library | `AuthenticationProvider`, `JwtService.issue_session` / `decode_session`, `SessionToken` |
| Vending domain/application | `Operator`, `ResolveOperator`, replenishment policies |

Forbidden in Vending domain/application: Google/JWT SDKs, home-grown crypto, trusting JWT `roles` as OperatorRole.

`GoogleOAuthProvider` (INTERNAL) may be wired only in `api/dependencies/auth_providers.py`.

---

## 5. Implemented vs Planned

| Item | Status |
| --- | --- |
| Monolito fachada | **Implemented** |
| `POST /api/v1/auth/session` | **Implemented** |
| `GET /api/v1/operators/me` | **Implemented** |
| Session JWT via Platform 1.11 (`tenant_id` claim) | **Implemented** |
| Harness `principal/...` | **Implemented** |
| Flutter client | **Planned** (V13) |
| OAuth/JWT inside Vending domain | **Forbidden** |

---

## 6. Mobile checklist

- [ ] Single Vending base URL
- [ ] Google Sign-In in the app; call `POST /api/v1/auth/session`
- [ ] Store `access_token`; send as Bearer on business calls
- [ ] Omit `X-Tenant-Id` or send the same tenant as the session
- [ ] Call `GET /operators/me` for Operator bootstrap
- [ ] Do not invent `principal/...` in production
- [ ] Do not treat JWT roles as Vending permissions
