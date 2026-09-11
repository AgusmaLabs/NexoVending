"""Map domain / platform errors to HTTP responses."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from nexo_platform.idempotency import (
    IdempotencyConflict,
    IdempotencyInProgress,
    IdempotencyKeyReuseConflict,
)
from nexo_platform.transaction import NestedTransactionError, TransactionConflict

from nexo_vending.domain.common.errors import (
    CapacityExceededError,
    DomainError,
    InsufficientStockError,
    InvalidReplenishmentStateError,
    SubstitutionRejectedError,
)
from nexo_vending.domain.identity.errors import IdentityError, OperatorNotFoundError


def _request_id(request: Request) -> str | None:
    context = getattr(request.state, "request_context", None)
    if context is not None:
        return str(context.request_id)
    return request.headers.get("X-Request-Id")


def _error(request: Request, *, status: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
            }
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(OperatorNotFoundError)
    async def operator_not_found(request: Request, exc: OperatorNotFoundError) -> JSONResponse:
        return _error(request, status=403, code="OPERATOR_NOT_FOUND", message=str(exc))

    @app.exception_handler(IdentityError)
    async def identity_error(request: Request, exc: IdentityError) -> JSONResponse:
        return _error(request, status=403, code="IDENTITY_ERROR", message=str(exc))

    @app.exception_handler(InsufficientStockError)
    async def insufficient_stock(request: Request, exc: InsufficientStockError) -> JSONResponse:
        return _error(request, status=409, code="INSUFFICIENT_INVENTORY", message=str(exc))

    @app.exception_handler(CapacityExceededError)
    async def capacity_exceeded(request: Request, exc: CapacityExceededError) -> JSONResponse:
        return _error(request, status=409, code="CAPACITY_EXCEEDED", message=str(exc))

    @app.exception_handler(SubstitutionRejectedError)
    async def substitution_rejected(
        request: Request, exc: SubstitutionRejectedError
    ) -> JSONResponse:
        return _error(request, status=409, code="SUBSTITUTION_REJECTED", message=str(exc))

    @app.exception_handler(InvalidReplenishmentStateError)
    async def invalid_state(
        request: Request, exc: InvalidReplenishmentStateError
    ) -> JSONResponse:
        return _error(request, status=409, code="INVALID_STATE", message=str(exc))

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        message = str(exc)
        code = "DOMAIN_ERROR"
        status = 409
        if "not found" in message.lower():
            return _error(request, status=404, code="NOT_FOUND", message=message)
        return _error(request, status=status, code=code, message=message)

    @app.exception_handler(IdempotencyKeyReuseConflict)
    async def idempotency_reuse(
        request: Request, exc: IdempotencyKeyReuseConflict
    ) -> JSONResponse:
        return _error(request, status=409, code="IDEMPOTENCY_KEY_REUSE", message=str(exc))

    @app.exception_handler(IdempotencyInProgress)
    async def idempotency_in_progress(
        request: Request, exc: IdempotencyInProgress
    ) -> JSONResponse:
        return _error(request, status=409, code="IDEMPOTENCY_IN_PROGRESS", message=str(exc))

    @app.exception_handler(IdempotencyConflict)
    async def idempotency_conflict(request: Request, exc: IdempotencyConflict) -> JSONResponse:
        return _error(request, status=409, code="IDEMPOTENCY_CONFLICT", message=str(exc))

    @app.exception_handler(TransactionConflict)
    async def transaction_conflict(request: Request, exc: TransactionConflict) -> JSONResponse:
        return _error(request, status=409, code="TRANSACTION_CONFLICT", message=str(exc))

    @app.exception_handler(NestedTransactionError)
    async def nested_transaction(request: Request, exc: NestedTransactionError) -> JSONResponse:
        return _error(request, status=500, code="NESTED_TRANSACTION", message=str(exc))

    @app.exception_handler(PermissionError)
    async def permission_denied(request: Request, exc: PermissionError) -> JSONResponse:
        return _error(request, status=403, code="FORBIDDEN", message=str(exc) or "forbidden")
