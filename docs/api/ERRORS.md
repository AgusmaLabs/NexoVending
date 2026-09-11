# HTTP errors

Stable envelope:

```json
{
  "error": {
    "code": "INSUFFICIENT_INVENTORY",
    "message": "…",
    "request_id": "<uuid>"
  }
}
```

`request_id` comes from Platform `RequestContext` (or `X-Request-Id` when present).

| Situation | HTTP | Typical code |
| --- | ---: | --- |
| Missing / invalid credentials | 401 | FastAPI detail |
| Permission / entitlement / operator | 403 | `FORBIDDEN`, `OPERATOR_NOT_FOUND` |
| Resource missing / cross-tenant | 404 | `NOT_FOUND` |
| Invalid state / capacity / stock / substitution / idempotency | 409 | `INVALID_STATE`, `CAPACITY_EXCEEDED`, … |
| Invalid JSON / schema | 422 | FastAPI validation |
| Unexpected | 500 | — |

Handlers: `api/error_handlers.py`.
