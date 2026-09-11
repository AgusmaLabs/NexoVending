# Versioning — NexoVending

NexoVending exposes **two independent version axes**. Mobile and frontend clients must follow the **HTTP API** axis. The Python package axis is for deploying and distributing the backend product.

```text
PACKAGE_VERSION  →  pip / Docker / release of the vending service
API_VERSION      →  URL prefix and JSON contract for HTTP clients
```

Current values (source of truth: `src/nexo_vending/versioning.py`):

| Axis | Value | Meaning |
| --- | --- | --- |
| Package | `0.2.0` | First mobile-ready HTTP surface with `/api/v1` |
| HTTP API | `v1` | Business routes under `/api/v1` |

## 1. What the frontend needs

Flutter / web clients **do not** install `nexo-vending` from pip.

They consume:

- Base URL of the running API (environment-specific)
- Versioned paths under `/api/v1/...`
- Auth headers documented in [MOBILE_API_CONTRACT.md](api/MOBILE_API_CONTRACT.md)
- OpenAPI at `/openapi.json` (or an exported snapshot)

Packaging the Python wheel remains required for **backend** distribution, CI clean-install, and deploy — not for the mobile repo.

## 2. HTTP API versioning (`v1`)

### Rules

- All business routes live under `/api/v1`.
- Probes stay unversioned: `GET /health`, `GET /health/ready`.
- OpenAPI UI stays at `/docs` (process root).
- Additive, backward-compatible changes stay in `v1` (new optional fields, new endpoints).
- Breaking changes require `/api/v2` (new mount) while `v1` remains until clients migrate.
- Do not silently change meaning of existing fields or status codes in `v1`.

### Override

Runtime prefix defaults to `/api/v1` (`Settings.api_prefix` / env `API_PREFIX`). Changing it in production without updating clients breaks them — treat as a release decision, not a local tweak.

## 3. Package SemVer (`nexo-vending`)

Follows [Semantic Versioning](https://semver.org/).

### MAJOR

Incompatible changes to the **deployable product** that operators or integrators must react to (for example removing a public Python entrypoint, or dropping support for an HTTP major that was still advertised).

### MINOR

Backward-compatible capabilities (new endpoints under the same HTTP major, new optional fields, new use cases).

### PATCH

Bug fixes and internal corrections that do not break HTTP or public Python contracts.

Package `info.version` in OpenAPI equals `PACKAGE_VERSION`. It is **not** the same string as `API_VERSION`.

## 4. Discovery for clients

```http
GET /health
```

```json
{
  "status": "ok",
  "package_version": "0.2.0",
  "api_version": "v1"
}
```

Export OpenAPI for offline codegen:

```bash
python scripts/export_openapi.py --out docs/api/openapi-v1.json
```

## 5. Compatibility with NexoPlatform

`nexo-vending` pins `nexo-platform==1.10.0`. Bumping Platform is a **package** dependency change and may ship without bumping HTTP `v1` if the public HTTP contract is unchanged.

## 6. Related docs

- [MOBILE_API_CONTRACT.md](api/MOBILE_API_CONTRACT.md)
- [ADR-031](adr/ADR-031-http-api-and-package-versioning.md)
- Platform policy (dependency only): NexoPlatform `docs/VERSIONING.md`
