# ADR-031 — HTTP API and package versioning

## Context

NexoVending’s HTTP API is about to be consumed by the mobile/frontend app. Until now business routes were mounted at the process root (`/replenishments`, …) with package version `0.1.0` duplicated in several places and no written versioning policy.

Frontend clients need a **stable HTTP contract**. They do not consume the Python wheel. Backend deploy still needs SemVer packaging.

## Decision

1. Introduce two explicit axes in `nexo_vending.versioning`:
   - `PACKAGE_VERSION` (SemVer for the pip/Docker product)
   - `API_VERSION` / `API_PREFIX` (`v1` → `/api/v1`)
2. Mount all business routers under `/api/v1`.
3. Keep `/health` and `/health/ready` unversioned for probes; include `package_version` and `api_version` in their payloads.
4. Bump package to `0.2.0` as the first mobile-ready, URL-versioned release.
5. Document the policy in `docs/VERSIONING.md` and point mobile developers at `/api/v1` + OpenAPI export.

## Consequences

- Clients must call `/api/v1/...` (breaking vs the previous unversioned paths; acceptable before mobile lock-in).
- Future breaking HTTP changes go to `/api/v2` without forcing an immediate package major unless the product contract requires it.
- OpenAPI `info.version` tracks the package; HTTP major is visible via prefix and `/health`.

## Alternatives considered

- **Header-only API versioning** — rejected; URL major is easier for mobile base URL configuration and OpenAPI path grouping.
- **Ship a typed mobile SDK package from this repo** — deferred; OpenAPI + contract docs are enough for the first frontend iteration.
- **Keep unversioned paths** — rejected; locks clients into an unstable root namespace.
