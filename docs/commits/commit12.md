# Commit V12 — Mobile Session JWT Facade

**Commit message**

`feat(auth): consume Platform 1.11 session JWT via monolito facade`

## 1. Objetivo

Implementar el **facade HTTP de sesión móvil** de `nexo-vending`, consumiendo las APIs públicas de sesión JWT de `nexo-platform==1.11.0`, para que Flutter hable con **una sola base URL** sin que Vending implemente OAuth, JWT ni Google Sign-In.

El facade debe:

* aceptar un `id_token` de Google (IdP) ya obtenido en el cliente;
* autenticar vía `AuthenticationProvider` de Platform;
* aceptar un `tenant_id` de producto **solo** en este endpoint;
* exigir un `Operator` Vending provisionado para `(tenant, principal)` antes de emitir token;
* emitir sesión con `JwtService.issue_session` (RS256, `tenant_id` en el claim);
* validar llamadas de negocio con `JwtService.decode_session`;
* construir `RequestContext` desde `SessionToken.principal` + `SessionToken.tenant_id`;
* exponer `GET /operators/me` como bootstrap post-auth;
* mantener el harness `Bearer principal/<provider>/<subject>` para tests/CI.

La autenticación, emisión/verificación JWT y validación de `id_token` deben continuar siendo provistas por:

```text
nexo-platform==1.11.0
```

No implementar el cliente Flutter en V12.

---

# 2. Frontera arquitectónica

La responsabilidad queda dividida así:

```text
┌──────────────────────────────────────────────┐
│           nexo-platform 1.11.0               │
│                                              │
│ AuthenticationProvider                       │
│ AuthenticationCredentials                    │
│ AuthenticationResult                         │
│ Principal                                    │
│ JwtService                                   │
│   issue_session / decode_session / jwks      │
│ SessionToken                                 │
│ RequestContext                               │
│ GoogleOAuthProvider (INTERNAL; composition)  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                nexo-vending                  │
│                                              │
│ HTTP POST /api/v1/auth/session               │
│ HTTP GET  /api/v1/operators/me               │
│ auth.py  Bearer JWT | principal harness      │
│ IssueOperatorSession                         │
│ GetCurrentOperator                           │
│ ResolveOperator                              │
│ Operator role / status / validity            │
│ Business permissions & entitlements          │
└──────────────────────────────────────────────┘
```

## Regla

Vending **no debe implementar nuevamente**:

```text
JWT crypto (HS256/RS256/JWKS)
Google OAuth / ID token validation
Argon2 / password login
Platform User as replenisher identity
```

Vending solamente consume esas capacidades desde Platform en Application (contratos públicos) y en el composition root (adapter Google INTERNAL).

---

# 3. Dependencia

Actualizar Vending para consumir:

```text
nexo-platform==1.11.0
```

mediante el mecanismo de distribución ya establecido:

```text
vendor/nexo_platform-1.11.0-*.whl
```

y el pin en `pyproject.toml`.

No copiar código de:

```text
nexo_platform/identity
```

dentro de Vending.

Contrato público de referencia:

* `docs/NexoPlatform/Platform_Public_API.md` (release `1.11.0`)
* `docs/NexoPlatform/Platform_Consumer_Guide.md` (receta session JWT)

---

# 4. Qué consume Vending de Platform

Desde APIs **públicas**:

```python
from nexo_platform.identity import (
    JwtService,
    SessionToken,
    AuthenticationProvider,
    AuthenticationCredentials,
    AuthenticationResult,
    Principal,
)
from nexo_platform.context import RequestContext
```

(o los re-exports equivalentes de `nexo_platform.identity.authentication` / `nexo_platform.tenant` ya usados).

Receta de sesión (Consumer Guide):

```python
session: SessionToken = jwt_service.issue_session(result, tenant_id=accepted_tenant_id)

session = jwt_service.decode_session(access_token)
context = RequestContext.from_principal(
    principal=session.principal,
    tenant_id=session.tenant_id,
)
```

`JwtService` / `SessionToken` **no** son root exports; importar desde `nexo_platform.identity`.

---

# 5. Qué NO consume Vending como dominio

Aunque Platform tenga:

```text
identity.presentation /login  (password → Platform User)
identity.infrastructure.oauth.google.GoogleOAuthProvider
identity.application.services.jwt_service internals
```

Vending **no** monta el `/login` de Platform User como login de reponedores.

`Platform User ≠ Vending Operator`.

`GoogleOAuthProvider` es **INTERNAL** (`nexo_platform.identity.infrastructure`). Solo puede cablearse en el composition root:

```text
api/dependencies/  (factory)
```

Domain y Application importan únicamente el protocolo público `AuthenticationProvider`.

---

# 6. Modelo de sesión (no es un agregado de dominio)

V12 no introduce un agregado `Session` en el dominio Vending.

El token de sesión es un **hecho de Platform**:

```text
SessionToken
├── principal
├── tenant_id
└── (exp / access token string según contrato 1.11)
```

El dominio Vending sigue teniendo:

```text
Operator(tenant_id, principal, role, status, validity)
```

La sesión autentica identidad + tenant. Vending **autoriza** con Operator.

Por lo tanto:

```text
JWT roles  ≠  OperatorRole
JWT sub    →  Principal.subject
JWT tenant_id → RequestContext.tenant_id
```

---

# 7. Flujo monolito fachada

```text
Flutter
   │  Google Sign-In SDK → id_token
   ▼
POST /api/v1/auth/session
   { "id_token": "...", "tenant_id": "tnnt_998877" }
   │
   ▼
AuthenticationProvider.authenticate
   credentials.kind = "id_token"
   │
   ▼
AuthenticationResult + Principal
   │
   ▼
product accepts tenant_id
   │
   ▼
ResolveOperator(tenant, principal)
   ├── missing → 403 (no issue token)
   └── found  → continue
   │
   ▼
JwtService.issue_session(result, tenant_id=accepted)
   │
   ▼
{ access_token, token_type: "Bearer", expires_in }
   │
   ▼
Flutter stores access_token
   │
   ▼
GET/POST /api/v1/...
Authorization: Bearer <JWT>
X-Tenant-Id: optional (must match claim if present)
   │
   ▼
JwtService.decode_session
   │
   ▼
RequestContext.from_principal(principal, tenant_id=session.tenant_id)
   │
   ▼
ResolveOperator → business authorization
```

---

# 8. Tenant

## En el facade de sesión

El body **puede** incluir `tenant_id` porque es el paso de **aceptación de producto** (el operador elige tenant activo). No es autoridad ciega: Vending comprueba que existe `Operator` para ese tenant + principal autenticado.

```text
id_token  →  Principal (Platform)
tenant_id →  accepted only if Operator exists
        ↓
issue_session embeds tenant_id in JWT
```

## En rutas de negocio

Nunca tomar `tenant_id` del JSON como autoridad.

Tras `decode_session`:

```text
session.tenant_id  =  autoridad
X-Tenant-Id        =  opcional; si existe debe coincidir; si falta se usa el claim
```

Si `X-Tenant-Id` no coincide con el claim → **401**.

El harness de tests sigue exigiendo `X-Tenant-Id` cuando el Bearer es `principal/...` (no hay claim).

---

# 9. IssueOperatorSession

Crear:

```text
nexo_vending/application/identity/issue_session.py
```

No nombrar el archivo `jwt*.py` ni `oauth*.py` (architecture tests de nombres).

Comando conceptual:

```python
IssueOperatorSessionCommand(
    id_token: str,
    tenant_id: str,
)
```

Flujo:

```text
1. AuthenticationCredentials(kind="id_token", attributes={"id_token": ...})
2. provider.authenticate(credentials) → AuthenticationResult
3. Build RequestContext.from_principal(principal, tenant_id=command.tenant_id)
4. ResolveOperator — OperatorNotFoundError → no emitir token
5. jwt_service.issue_session(result, tenant_id=accepted)
6. Return SessionToken / access_token + expires_in
```

El use case depende de:

```text
AuthenticationProvider   # Protocol público Platform
JwtService               # Público Platform
OperatorRepository       # Port Vending (vía ResolveOperator)
```

No depende de FastAPI, Google SDK ni `identity.infrastructure`.

---

# 10. GetCurrentOperator

Crear:

```text
nexo_vending/application/identity/get_current_operator.py
```

o reutilizar `ResolveOperator` expuesto por HTTP.

`GET /api/v1/operators/me` (autenticado):

```text
RequestContext (ya resuelto por auth.py)
        ↓
ResolveOperator
        ↓
OperatorOut  (id, tenant, role, status, display_name, …)
```

No es OAuth. Es bootstrap de sesión de negocio para Flutter.

JWT `roles` no se copian a la respuesta como autoridad; se serializa el `OperatorRole` de Vending.

---

# 11. HTTP adapter

Crear:

```text
nexo_vending/api/routers/auth_session.py
```

Montar en `api/router.py` bajo `/api/v1`.

### POST `/auth/session`

Sin Bearer previo (el `id_token` es la credencial).

Request:

```json
{
  "id_token": "<google_id_token>",
  "tenant_id": "tnnt_998877"
}
```

Response 200:

```json
{
  "access_token": "<jwt>",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

Errores:

| Caso | HTTP |
| --- | ---: |
| `id_token` inválido / expirado (Platform auth error) | 401 |
| Operator no existe para tenant + principal | 403 |
| Body sin `id_token` / `tenant_id` | 422 |

Idempotency-Key no es obligatorio (emisión de token no es un comando de inventario). Si se envía, no debe duplicar side effects de negocio (no hay).

### GET `/operators/me`

Requiere el mismo auth que el resto de `/api/v1`.

Success 200: representación pública del Operator.

403 si no hay Operator / políticas de identidad.

---

# 12. auth.py — dual credential

Extender `src/nexo_vending/api/dependencies/auth.py` **sin** crear `jwt.py`.

```text
Authorization: Bearer <credential>
```

1. Si `credential` empieza por `principal/` → comportamiento V9 (harness). `X-Tenant-Id` **requerido**.
2. Else → `JwtService.decode_session(credential)`:
   * fallido / expirado → 401
   * `tenant_id` del token = autoridad
   * si `X-Tenant-Id` presente y no coincide → 401
   * `RequestContext.from_principal(session.principal, tenant_id=session.tenant_id)`

`auth_context_override` de tests se mantiene.

JwtService se inyecta desde app state / factory (composition root), no se construye con secretos en el dominio.

---

# 13. Composition root / wiring

En `api/dependencies` (o factory existente):

```text
JwtService          ← Platform public, keys/issuer from product config
AuthenticationProvider ← GoogleOAuthProvider wired HERE only
```

Configuración de producto (env), no hardcoded:

```text
VENDING_JWT_* / Platform identity settings según 1.11
GOOGLE OIDC client settings para el adapter INTERNAL
```

JWKS: si Platform expone `JwtService.jwks` (o equivalente público), Vending **puede** montar `GET /api/v1/auth/jwks` como pasamanos delgadísimo **solo si** hace falta a un cliente externo. Flutter in-process no lo necesita para llamar Vending. Por defecto V12 **no** publica JWKS salvo que el contrato 1.11 lo requiera para el facade; documentar como opcional.

No importar `nexo_platform.identity.infrastructure` desde:

```text
domain/
application/
```

Architecture test: allowlist de un único módulo de composition (p.ej. `api/dependencies/auth_providers.py`) para el import INTERNAL.

---

# 14. Nombres de archivos (constraint)

Prohibido en `src/nexo_vending`:

```text
*jwt*.py
*oauth*.py
*google*.py
```

Permitido:

```text
application/identity/issue_session.py
application/identity/get_current_operator.py
api/routers/auth_session.py
api/dependencies/auth.py          # existente
api/dependencies/auth_providers.py
```

---

# 15. Qué NO hace V12

* Cliente Flutter (V13+).
* Offline / sync.
* Refresh token propio de Vending.
* Password `/login` de Platform User.
* Auto-provision de Operator en el login (sigue siendo administración V3).
* Cambiar reglas de reposición / inventario.
* Reescribir crypto JWT en Vending.
* Tratar `roles` del JWT como `OperatorRole`.

---

# 16. Relación con ADRs existentes

* **ADR-006** — Platform owns authentication; V12 consume 1.11, no duplica.
* **ADR-029** — actualizar: el adapter de producción ya no es “future swap”; Bearer puede ser session JWT de Platform. Harness `principal/...` permanece.
* **ADR-008 / identity Operator** — sin cambio de agregado.
* Nuevo **ADR-033 — Monolith session facade**: Vending es la única puerta HTTP; Platform emite/verifica JWT; tenant claim es autoridad post-sesión.

---

# 17. Tests de Application — IssueOperatorSession

```text
test_issue_session_authenticates_id_token_via_provider
test_issue_session_rejects_invalid_id_token
test_issue_session_rejects_unprovisioned_operator
test_issue_session_embeds_accepted_tenant_in_platform_session
test_issue_session_does_not_use_jwt_roles_as_operator_role
```

Usar `AuthenticationProvider` fake en unit/application tests (no red a Google).

---

# 18. Tests de GetCurrentOperator / me

```text
test_me_returns_vending_operator_from_request_context
test_me_rejects_missing_operator
test_me_ignores_claimed_operator_id
```

---

# 19. Tests de auth.py (dual credential)

```text
test_harness_principal_token_still_requires_x_tenant_id
test_session_jwt_builds_context_from_decode_session_tenant
test_session_jwt_rejects_mismatched_x_tenant_id
test_session_jwt_allows_omitted_x_tenant_id
test_expired_or_invalid_jwt_returns_401
test_auth_context_override_still_works
```

---

# 20. Tests de API

```text
test_post_auth_session_returns_bearer_token
test_post_auth_session_invalid_id_token_401
test_post_auth_session_unknown_operator_403
test_post_auth_session_validation_error_422
test_get_operators_me_with_session_jwt_200
test_business_route_accepts_session_jwt_without_inventing_principal_token
test_business_route_still_accepts_harness_principal_token
```

---

# 21. Tests de tenant isolation

```text
test_cannot_issue_session_for_operator_of_other_tenant
test_decode_session_tenant_cannot_be_overridden_by_body_on_business_routes
test_x_tenant_id_mismatch_on_jwt_is_401
```

---

# 22. Tests Platform integration contract

Demostrar round-trip real de `nexo-platform==1.11.0`:

```text
AuthenticationResult (fake or test principal)
        ↓
JwtService.issue_session(..., tenant_id=...)
        ↓
JwtService.decode_session
        ↓
session.principal + session.tenant_id
        ↓
RequestContext.from_principal
```

El test debe usar el `JwtService` **del paquete instalado**, no una copia local.

```text
test_consumes_nexo_platform_1_11_0
test_issue_and_decode_session_come_from_nexo_platform_package
test_session_token_type_is_platform_session_token
```

Si `issue_session` requiere claves RS256 de test, generarlas en el test/composition de test **sin** implementar un JwtService de Vending.

---

# 23. Tests de arquitectura

Extender:

```text
test_consumes_nexo_platform_1_11_0          # pin bump from 1.10.0
test_domain_does_not_import_identity_infrastructure
test_application_does_not_import_identity_infrastructure
test_application_does_not_import_fastapi
test_vending_does_not_implement_local_oauth_or_jwt   # filenames
test_vending_does_not_import_provider_sdks           # google.oauth2, jose, …
test_google_oauth_provider_import_only_in_composition_root
test_no_copied_platform_identity_tree
```

---

# 24. Security / authorization tests

```text
test_session_does_not_grant_replenish_if_operator_inactive
test_session_does_not_grant_replenish_if_operator_admin_only_policy
test_jwt_roles_claim_ignored_for_can_operator_replenish
```

La cadena permanece:

```text
Platform Principal
        ↓
Vending Operator
        ↓
Role / Status / Validity
        ↓
Business authorization
```

---

# 25. Documentación

Actualizar / agregar:

```text
docs/
├── commits/
│   ├── commit12.md
│   └── secuencia.md
├── api/
│   ├── MOBILE_AUTHENTICATION_CONTRACT.md   # session Implemented vía 1.11
│   ├── MOBILE_API_CONTRACT.md              # POST /auth/session, GET /operators/me
│   └── openapi-v1.json                     # export
├── adr/
│   ├── ADR-029-vending-http-api-boundary.md  # dual credential
│   └── ADR-033-monolith-session-facade.md
├── architecture/
│   ├── IDENTITY_BOUNDARY.md
│   └── PLATFORM_INTEGRATION.md
├── security/
│   └── OPERATOR_ACCESS_MODEL.md
README.md / ARCHITECTURE.md / pyproject.toml pin 1.11.0
```

Marcar explícitamente:

| Item | Status after V12 |
| --- | --- |
| Harness `principal/...` | **Implemented** (tests) |
| POST `/auth/session` + decode_session | **Implemented** |
| RS256 + `tenant_id` claim | **Implemented** (Platform 1.11, consumed) |
| Flutter client | **Planned** (V13) |
| OAuth inside Vending domain | **Forbidden** |

---

# 26. ADR-033 — Monolith session facade

**Context**

Flutter necesita una sola URL. Platform 1.11 publica `issue_session` / `decode_session` / `SessionToken`. Vending no debe ser IdP.

**Decision**

1. NexoVending es la única puerta HTTP del móvil en esta etapa.
2. `POST /api/v1/auth/session` es un adapter delgado: authenticate + accept tenant + issue_session.
3. Rutas de negocio validan Bearer JWT con `decode_session`; `session.tenant_id` es autoridad.
4. `GoogleOAuthProvider` solo en composition root.
5. Operator Vending sigue siendo la autorización.

**Consequences**

* Bump a `nexo-platform==1.11.0`.
* `X-Tenant-Id` deja de ser obligatorio en presencia de JWT de sesión.
* Extraer un gateway HTTP separado más adelante no cambia el dominio; solo el composition root.

**Alternatives considered**

1. Gateway Platform separado ahora — rechazado (dos hosts).
2. JWT/OAuth implementado en Vending — rechazado (ADR-006).
3. Seguir solo con `principal/...` en producción — rechazado (Flutter no debe inventar el token).

---

# 27. Criterios de aceptación

El Commit V12 se considera aprobado solamente si:

## Platform dependency

* [ ] `nexo-vending` consume `nexo-platform==1.11.0`.
* [ ] utiliza `JwtService.issue_session` / `decode_session` del paquete.
* [ ] utiliza `SessionToken` de Platform.
* [ ] utiliza `AuthenticationProvider` / `AuthenticationResult` / `Principal`.
* [ ] no duplica JwtService.
* [ ] no implementa validación Google/JWKS propia.
* [ ] no monta password `/login` de Platform User.

## Session facade

* [ ] existe `POST /api/v1/auth/session`.
* [ ] body `id_token` + `tenant_id`.
* [ ] operator inexistente → no hay token (403).
* [ ] `id_token` inválido → 401.
* [ ] respuesta `access_token` / `Bearer` / `expires_in`.

## Request auth

* [ ] Bearer JWT → `decode_session` → RequestContext.
* [ ] `session.tenant_id` es autoridad.
* [ ] `X-Tenant-Id` opcional y debe coincidir.
* [ ] harness `principal/...` + `X-Tenant-Id` sigue funcionando.

## Operator bootstrap

* [ ] existe `GET /api/v1/operators/me`.
* [ ] serializa Operator Vending, no Platform User ni JWT roles.

## Tenant isolation

* [ ] negocio no acepta `tenant_id` de body como autoridad.
* [ ] no se emite sesión cross-tenant.
* [ ] mismatch de header vs claim → 401.

## Architecture

* [ ] domain no importa `identity.infrastructure`.
* [ ] application no importa `identity.infrastructure`.
* [ ] no existen archivos `jwt*` / `oauth*` / `google*` bajo `src/nexo_vending`.
* [ ] GoogleOAuthProvider solo en composition root allowlisted.
* [ ] domain no depende de FastAPI / SQLAlchemy / Google / jose.
* [ ] `nexo-platform → nexo-vending` no existe.

## Tests

* [ ] application issue session;
* [ ] API session + me;
* [ ] dual credential auth;
* [ ] tenant isolation;
* [ ] Platform 1.11 round-trip;
* [ ] architecture pin 1.11.0;
* [ ] harness regression V9–V11.

## Quality

* [ ] `pytest` pasa;
* [ ] `ruff check` pasa;
* [ ] OpenAPI export actualizado;
* [ ] clean install resuelve `nexo-platform==1.11.0`;
* [ ] Docker smoke / Testcontainers baseline OK.

## Documentation

* [ ] ADR-033 creado;
* [ ] ADR-029 actualizado;
* [ ] MOBILE_AUTHENTICATION_CONTRACT refleja Implemented vs Planned;
* [ ] MOBILE_API_CONTRACT lista los endpoints nuevos;
* [ ] pin 1.11.0 en README / ARCHITECTURE / PLATFORM_INTEGRATION;
* [ ] `secuencia.md` apunta V12 a este commit.

---

# 28. Definition of Done

V12 queda cerrado cuando:

```text
nexo-platform==1.11.0
      +
POST /api/v1/auth/session
      +
JwtService.issue_session / decode_session
      +
RequestContext from SessionToken
      +
GET /operators/me
      +
harness principal/... preserved
      +
Operator authorization unchanged
      +
Tests
      +
Architecture rules
      +
Documentation
```

están implementados y validados.

No debe existir todavía:

```text
Flutter app
Offline SQLite sync
Vending-owned refresh token store
Google OAuth implemented in Vending domain
Platform password login as replenisher login
```

---

# 29. Resultado arquitectónico

Al terminar V12:

```text
                  Flutter (V13+)
                         │
                         │ single host
                         ▼
                  nexo-vending HTTP
                         │
            ┌────────────┴────────────┐
            ▼                         ▼
     auth_session adapter      business routers
            │                         │
            ▼                         ▼
     AuthenticationProvider     decode_session
     issue_session                    │
            │                         ▼
            └──────────► RequestContext
                              │
                              ▼
                        ResolveOperator
                              │
                              ▼
                           Operator
```

```text
                  nexo-platform 1.11.0
                         │
                         │ JwtService / SessionToken
                         │ AuthenticationProvider
                         │ RequestContext
                         ▼
                  nexo-vending adapters
                         │
                         ▼
                  Vending Operator & use cases
```

Este diseño deja el backend listo para que **V13 Flutter** consuma `POST /auth/session` y las APIs de reposición ya existentes, sin introducir lógica de negocio ni crypto en el cliente.
