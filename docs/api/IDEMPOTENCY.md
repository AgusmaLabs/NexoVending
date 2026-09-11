# HTTP idempotency

Status: **Implemented** (V9) via Platform `IdempotencyService` (`nexo-platform>=1.8`).

## Client

Send on mutating requests:

```http
Idempotency-Key: <opaque-string>
```

Same tenant + operation + key + payload hash → replay stored HTTP result.  
Same key + different payload hash → `409 IDEMPOTENCY_KEY_REUSE`.

## Server

```text
SqlAlchemyTransactionalUnitOfWork(session)
  └── IdempotencyService.for_session(session).execute(...)
        └── application use case (same Session)
```

No `VendingIdempotencyService`. Domain keys (replenishment / movement) may coexist.

## Schema

Platform owns `platform_idempotency_records`. Run Platform migrations on shared DB; Vending tests create the table in the API fixture when needed.
