# Commit 3 — Identity & Operator Management

**Commit message**

`feat(vending): add tenant-scoped identity and operator management`

## 1. Objetivo

Implementar la identidad y gestión de operadores propia de `nexo-vending`, **consumiendo exclusivamente las capacidades de Identity/Authentication de `nexo-platform==1.2.0`**.

Este commit establece la frontera entre:

```text
Platform Authentication
        ↓
Authenticated Principal
        ↓
Vending Identity
        ↓
Vending Authorization
```

`nexo-vending` no implementa OAuth, Google OAuth, JWT ni autenticación propia.

---

# 2. Regla arquitectónica principal

La autenticación pertenece a Platform.

La autorización específica de Vending pertenece a Vending.

Por lo tanto:

```text
                    NEXO PLATFORM 1.2.0
              ┌─────────────────────────────┐
              │ AuthenticationProvider      │
              │ AuthenticationCredentials   │
              │ AuthenticationResult        │
              │ AuthenticatedIdentity       │
              │ ExternalIdentity            │
              │ Principal                   │
              │ GoogleOAuthProvider         │
              │ JwtService                  │
              │ RequestContext              │
              └──────────────┬──────────────┘
                             │
                             │ consumed as package
                             ▼
                    NEXO VENDING
              ┌─────────────────────────────┐
              │ User                        │
              │ Operator                    │
              │ Role                        │
              │ Status                      │
              │ ValidityPeriod              │
              │ Authorization               │
              └─────────────────────────────┘
```

La dependencia debe permanecer:

```text
nexo-vending → nexo-platform
```

Nunca:

```text
nexo-platform → nexo-vending
```

---

# 3. Dependencia

Actualizar Vending para consumir:

```text
nexo-platform==1.2.0
```

mediante el mecanismo de distribución ya establecido en V0:

```text
vendor/nexo_platform-1.2.0-*.whl
```

No copiar código de:

```text
nexo_platform/identity
```

dentro de Vending.

---

# 4. Qué consume Vending de Platform

Vending debe importar desde Platform los contratos existentes:

```python
from nexo_platform.identity.authentication import (
    AuthenticatedIdentity,
    AuthenticationProvider,
    AuthenticationResult,
    ExternalIdentity,
    Principal,
)
```

y, cuando corresponda:

```python
from nexo_platform.tenant.request_context import RequestContext
```

No crear versiones locales de:

```text
AuthenticatedIdentity
ExternalIdentity
Principal
AuthenticationProvider
AuthenticationCredentials
AuthenticationResult
```

---

# 5. Qué NO consume Vending como dominio

Aunque Platform tenga un `identity.domain.entities.User`, Vending **no debe utilizar ese User como su operador de negocio**.

El `User` de Platform representa una cuenta de Platform.

Vending necesita su propio modelo de negocio:

```text
VendingUser / Operator
```

porque debe manejar reglas que no pertenecen al core transversal:

* activación por administrador Vending;
* vigencia del operador;
* rol dentro de Vending;
* autorización para reponer;
* futuras asignaciones de máquinas;
* futuras restricciones operativas.

Esta distinción es fundamental.

```text
Platform User
    ≠
Vending Operator
```

---

# 6. Modelo de Vending Identity

Crear:

```text
nexo_vending/domain/identity/
├── entities.py
├── value_objects.py
├── enums.py
├── errors.py
└── policies.py
```

---

# 7. Operator

El concepto principal de negocio será `Operator`.

No necesitamos duplicar toda la identidad externa.

El operador tendrá una referencia a la identidad autenticada de Platform mediante una abstracción estable.

Recomendación:

```python
Operator(
    id: OperatorId,
    tenant_id: TenantId,
    principal: Principal,
    email: Email | None,
    display_name: str | None,
    role: OperatorRole,
    status: OperatorStatus,
    validity_period: ValidityPeriod,
)
```

El `Principal` es el objeto de Platform.

Vending no reconstruye:

```text
provider
subject
```

manualmente.

---

# 8. Principal como vínculo entre Platform y Vending

El vínculo conceptual será:

```text
Platform Principal
        │
        │ identity binding
        ▼
Vending Operator
```

Ejemplo:

```text
Principal
provider = "google"
subject = "123456789"
```

corresponde a:

```text
Operator
tenant = tenant-A
role = OPERATOR
status = ACTIVE
```

La misma identidad externa podría pertenecer a otro tenant como una entidad Vending diferente:

```text
Google Principal X
       │
       ├── tenant-A → Operator
       │
       └── tenant-B → Operator
```

Por eso el lookup debe ser siempre tenant-scoped.

---

# 9. OperatorStatus

Definir:

```python
class OperatorStatus(Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"
```

Semántica:

### PENDING

La identidad existe pero aún no tiene autorización operacional.

### ACTIVE

Puede realizar operaciones permitidas por Vending.

### SUSPENDED

Operador temporalmente bloqueado.

### DISABLED

Operador deshabilitado.

---

# 10. OperatorRole

Inicialmente:

```python
class OperatorRole(Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
```

No utilizar los roles de Platform para representar automáticamente roles de Vending.

Platform puede entregar información de autenticación/autorización transversal.

Vending decide sus propias reglas.

---

# 11. ValidityPeriod

Crear:

```python
ValidityPeriod(
    valid_from: datetime,
    valid_until: datetime | None,
)
```

Reglas:

```text
valid_from < valid_until
```

cuando `valid_until` exista.

Semántica:

```text
[valid_from, valid_until)
```

Método:

```python
is_valid_at(timestamp)
```

Debe funcionar con timestamps timezone-aware.

---

# 12. Regla de autorización operacional

Crear una política de dominio:

```python
can_operator_replenish(operator, at)
```

La operación sólo es válida cuando:

```text
status == ACTIVE
AND
role == OPERATOR
AND
validity_period.is_valid_at(at)
```

El administrador podrá tener otras capacidades:

```text
can_manage_operators()
can_manage_inventory()
can_manage_machines()
```

pero esas reglas deben mantenerse separadas de la autenticación.

---

# 13. Lifecycle

Transiciones permitidas:

```text
PENDING
   │
   └── activate ──→ ACTIVE
                       │
                       ├── suspend ──→ SUSPENDED
                       │                  │
                       │                  └── activate → ACTIVE
                       │
                       └── disable ──→ DISABLED

SUSPENDED
   │
   └── disable ──→ DISABLED
```

`DISABLED` será terminal en V3.

No permitir:

```text
DISABLED → ACTIVE
DISABLED → PENDING
```

---

# 14. Application layer

Crear:

```text
nexo_vending/application/identity/
├── provision_operator.py
├── activate_operator.py
├── suspend_operator.py
├── disable_operator.py
├── assign_operator_role.py
└── resolve_operator.py
```

## ProvisionOperator

Recibe una identidad autenticada de Platform:

```python
AuthenticatedIdentity
```

o su `Principal` acompañado del contexto necesario.

Crea o recupera el operador Vending correspondiente.

Nunca recibe:

```text
google_access_token
google_id_token
authorization_code
```

como concepto de dominio.

Eso pertenece a Platform.

---

# 15. ResolveOperator

Flujo:

```text
HTTP authentication
        │
        ▼
nexo-platform
GoogleOAuthProvider
        │
        ▼
AuthenticationResult
        │
        ▼
Principal
        │
        ▼
RequestContext
        │
        ▼
Vending ResolveOperator
        │
        ▼
tenant_id + principal
        │
        ▼
Operator
```

La búsqueda debe utilizar:

```text
tenant_id
+
principal.provider
+
principal.subject
```

como identidad contextual.

---

# 16. RequestContext

Vending debe consumir el `RequestContext` proporcionado por Platform.

Particularmente:

```python
context.tenant_id
context.principal
```

El tenant **no debe provenir del request body**.

El actor autenticado tampoco debe ser tomado de un `user_id` arbitrario enviado por el cliente.

---

# 17. Regla de seguridad

Incorrecto:

```json
{
    "tenant_id": "...",
    "operator_id": "..."
}
```

como fuente de autoridad.

Correcto:

```text
RequestContext
├── tenant_id
└── principal
       │
       ▼
ResolveOperator
```

El `operator_id` se deriva de la identidad autenticada y del tenant.

---

# 18. Repository contracts

Crear:

```python
OperatorRepository
```

con:

```python
get(operator_id)
save(operator)
find_by_principal(tenant_id, principal)
```

No implementar PostgreSQL todavía.

El repository será un port.

La persistencia pertenece a un commit posterior.

---

# 19. Autenticación

Vending **no crea**:

```text
GoogleOAuthProvider
Google OAuth client
Google token validator
JWT implementation
OAuth callback
```

Todo eso ya pertenece a:

```text
nexo-platform==1.2.0
```

Vending solamente consume:

```python
AuthenticationProvider
```

cuando necesite integrar el flujo de autenticación en su application/presentation layer.

---

# 20. No acoplar Vending a Google

Aunque V3 inicialmente use Google, Vending no debe contener:

```python
if provider == "google":
```

para resolver comportamiento de negocio.

Debe trabajar con:

```python
Principal
```

o:

```python
AuthenticatedIdentity
```

El provider queda como metadata de identidad.

---

# 21. Tests de Value Objects

Crear:

```text
tests/unit/domain/identity/test_value_objects.py
```

### Email

```text
test_email_normalizes_case
test_email_trims_whitespace
test_email_rejects_empty
test_email_rejects_invalid_format
```

### ValidityPeriod

```text
test_validity_period_accepts_open_end
test_validity_period_accepts_valid_range
test_validity_period_rejects_reversed_range
test_validity_period_is_valid_inside_range
test_validity_period_is_invalid_before_start
test_validity_period_is_invalid_at_end
```

---

# 22. Tests de Operator

```text
test_operator_requires_tenant
test_operator_requires_principal
test_operator_starts_pending
test_operator_can_be_activated
test_operator_can_be_suspended
test_operator_can_be_disabled
```

---

# 23. Tests de lifecycle

```text
test_pending_can_activate
test_active_can_suspend
test_suspended_can_activate
test_active_can_disable
test_suspended_can_disable
test_disabled_is_terminal
test_disabled_cannot_activate
test_disabled_cannot_suspend
```

---

# 24. Tests de autorización

```text
test_active_operator_can_replenish
test_pending_operator_cannot_replenish
test_suspended_operator_cannot_replenish
test_disabled_operator_cannot_replenish
test_operator_before_validity_cannot_replenish
test_operator_after_validity_cannot_replenish
test_operator_at_validity_start_can_replenish
test_operator_at_validity_end_cannot_replenish
```

---

# 25. Tests de tenant isolation

Estos son obligatorios.

```text
test_operator_lookup_is_tenant_scoped
test_same_principal_can_exist_in_different_tenants
test_operator_from_other_tenant_is_not_resolved
test_cross_tenant_operator_access_is_rejected
```

Caso:

```text
Principal:
    google / 123

Tenant A:
    Operator ACTIVE

Tenant B:
    Operator SUSPENDED
```

Una request dentro de Tenant B nunca debe resolver accidentalmente al operador de Tenant A.

---

# 26. Tests Platform integration contract

Crear tests que importen el paquete real:

```python
from nexo_platform.identity.authentication import (
    AuthenticatedIdentity,
    ExternalIdentity,
    Principal,
)
```

y verifiquen que Vending utiliza esos objetos directamente.

Por ejemplo:

```text
test_vending_accepts_platform_principal
test_vending_accepts_platform_authenticated_identity
test_operator_preserves_platform_principal
```

No crear mocks que reproduzcan manualmente las clases de Platform.

---

# 27. Test crítico de arquitectura

Agregar:

```text
tests/architecture/test_platform_identity_boundary.py
```

Debe fallar si Vending introduce:

```text
nexo_vending/**/google*.py
nexo_vending/**/oauth*.py
nexo_vending/**/jwt*.py
```

como implementación propia.

También debe detectar imports como:

```text
google.oauth2
google.auth
authlib
jose
```

dentro del dominio/application de Vending.

---

# 28. Test de consumo de Platform

Agregar un test que compruebe:

```text
nexo-vending
        ↓
nexo-platform==1.2.0
```

y no una copia local.

Conceptualmente:

```python
assert Principal.__module__.startswith("nexo_platform.")
```

y equivalente para:

```text
AuthenticatedIdentity
ExternalIdentity
AuthenticationResult
```

Esto protege explícitamente la decisión arquitectónica.

---

# 29. Test de Google boundary

No repetir los tests de Google OAuth de Platform.

Vending solamente debe verificar el contrato:

```text
Google OAuth
    ↓
Platform AuthenticationResult
    ↓
Vending ResolveOperator
```

El funcionamiento de Google OAuth ya es responsabilidad de la suite de Platform 1.2.0.

Esto evita duplicar cobertura y evita que Vending se acople al proveedor.

---

# 30. Application tests

Con repository fake:

```text
test_provision_operator
test_existing_operator_is_resolved
test_activate_operator
test_suspend_operator
test_disable_operator
test_assign_operator_role
```

Y especialmente:

```text
test_resolve_operator_uses_context_tenant
test_resolve_operator_uses_context_principal
test_client_cannot_override_tenant
test_client_cannot_override_actor
```

---

# 31. No persistencia todavía

V3 no crea:

```text
Alembic migration
PostgreSQL tables
SQLAlchemy models
```

La existencia de `Operator` en el dominio no implica todavía una tabla.

La persistencia deberá implementarse en un commit posterior.

Esto mantiene la separación:

```text
Domain Model
      ≠
Persistence Model
```

---

# 32. Documentación

Agregar:

```text
docs/
├── architecture/
│   └── IDENTITY_BOUNDARY.md
├── adr/
│   ├── ADR-005-platform-authentication.md
│   ├── ADR-006-vending-operator-identity.md
│   └── ADR-007-vending-authorization.md
└── security/
    └── OPERATOR_ACCESS_MODEL.md
```

---

# 33. ADR-005 — Platform Authentication

Decisión:

Toda autenticación transversal pertenece a `nexo-platform`.

Vending consume:

```text
AuthenticationProvider
AuthenticationResult
AuthenticatedIdentity
Principal
```

No implementa proveedores OAuth propios.

---

# 34. ADR-006 — Vending Operator Identity

Decisión:

`Operator` pertenece al dominio Vending.

Su identidad autenticada se vincula mediante `Principal` de Platform.

```text
Platform Principal
        +
Vending Tenant
        ↓
Vending Operator
```

Esto permite mantener separadas:

```text
authentication
identity
business role
authorization
```

---

# 35. ADR-007 — Vending Authorization

Decisión:

Platform proporciona identidad/autenticación transversal.

Vending determina si esa identidad puede realizar una operación Vending.

Ejemplo:

```text
Authenticated
        ↓
Principal
        ↓
Resolve Operator
        ↓
ACTIVE?
        ↓
Role?
        ↓
Validity?
        ↓
Can Replenish
```

---

# 36. OPERATOR_ACCESS_MODEL.md

Documentar la matriz inicial:

| Condición                    |                       Reponer |
| ---------------------------- | ----------------------------: |
| PENDING                      |                             ❌ |
| ACTIVE + OPERATOR + vigente  |                             ✅ |
| ACTIVE + OPERATOR + expirado |                             ❌ |
| SUSPENDED                    |                             ❌ |
| DISABLED                     |                             ❌ |
| ACTIVE + ADMIN               | según política administrativa |

Además documentar:

```text
Authentication:
    Platform

Identity:
    Vending

Authorization:
    Vending

Tenant:
    Platform RequestContext
```

---

# 37. Criterios de aceptación

El Commit 3 sólo se considera aprobado si:

## Platform integration

* [ ] `nexo-vending` consume `nexo-platform==1.2.0`.
* [ ] utiliza `Principal` de Platform.
* [ ] utiliza `AuthenticatedIdentity` de Platform cuando corresponda.
* [ ] no duplica `ExternalIdentity`.
* [ ] no duplica `AuthenticationProvider`.
* [ ] no duplica `AuthenticationResult`.
* [ ] no duplica JWT.
* [ ] no implementa Google OAuth.

## Identity

* [ ] existe `Operator`.
* [ ] Operator está asociado a tenant.
* [ ] Operator está asociado a `Principal`.
* [ ] existe `OperatorStatus`.
* [ ] existe `OperatorRole`.
* [ ] existe `ValidityPeriod`.

## Lifecycle

* [ ] las transiciones inválidas son rechazadas.
* [ ] `DISABLED` es terminal en V3.

## Authorization

* [ ] operador activo puede operar.
* [ ] operador pendiente no puede operar.
* [ ] operador suspendido no puede operar.
* [ ] operador deshabilitado no puede operar.
* [ ] operador fuera de vigencia no puede operar.

## Tenant isolation

* [ ] lookup de Operator siempre es tenant-scoped.
* [ ] no se acepta tenant desde payload como fuente de autoridad.
* [ ] no se acepta actor/operator arbitrario desde payload.

## Architecture

* [ ] Vending domain no importa Google.
* [ ] Vending application no implementa OAuth.
* [ ] Vending no implementa JWT.
* [ ] Vending no contiene una segunda implementación de Identity de Platform.
* [ ] `nexo-platform → nexo-vending` no existe.

## Tests

* [ ] unit tests.
* [ ] lifecycle tests.
* [ ] authorization tests.
* [ ] tenant isolation tests.
* [ ] Platform contract tests.
* [ ] architecture tests.
* [ ] V0/V1 regression suite.

## Quality

* [ ] Ruff limpio.
* [ ] type checking limpio, si forma parte del baseline.
* [ ] coverage no disminuye respecto del baseline.
* [ ] clean install funciona.
* [ ] Docker smoke continúa funcionando.
* [ ] Testcontainers/V0 continúa funcionando.

---

# 38. Definition of Done

El commit queda cerrado cuando la siguiente cadena funciona conceptualmente:

```text
Google
   ↓
nexo-platform 1.2.0
   ↓
AuthenticationResult
   ↓
Principal
   ↓
RequestContext
   ↓
nexo-vending
   ↓
ResolveOperator
   ↓
tenant + principal
   ↓
Operator
   ↓
status + role + validity
   ↓
authorized / rejected
```

Y queda explícitamente prohibida esta cadena:

```text
Google
   ↓
nexo-vending Google OAuth
```

---

# 39. Resultado final de V3

Al terminar el commit tendremos dos responsabilidades claramente separadas:

```text
┌───────────────────────────────────────────┐
│             NEXO PLATFORM 1.2.0           │
│                                           │
│ Authentication                            │
│ Google OAuth                              │
│ ExternalIdentity                         │
│ AuthenticatedIdentity                    │
│ Principal                                 │
│ JWT                                       │
│ RequestContext                            │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│               NEXO VENDING                │
│                                           │
│ Operator                                  │
│ OperatorRole                              │
│ OperatorStatus                            │
│ ValidityPeriod                            │
│ Operator lifecycle                        │
│ Vending authorization                     │
│ Tenant-scoped operator resolution         │
└───────────────────────────────────────────┘
```

Esto deja preparada la siguiente capa para persistir operadores sin volver a tocar la arquitectura de autenticación.
