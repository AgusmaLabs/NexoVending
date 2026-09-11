from fastapi import FastAPI
from nexo_platform.authorization import AuthorizationService
from nexo_platform.entitlement import EntitlementService
from nexo_platform.observability import Observability

from nexo_vending.api.error_handlers import register_exception_handlers
from nexo_vending.api.router import api_router
from nexo_vending.config import settings


def create_app(
    *,
    authorization: AuthorizationService | None = None,
    entitlements: EntitlementService | None = None,
    observability: Observability | None = None,
) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        description=(
            "NexoVending HTTP API for replenishment and inventory. "
            "Inbound adapter over application use cases; uses Platform "
            "RequestContext, TransactionalUnitOfWork, Idempotency, and Observability."
        ),
        version="0.1.0",
    )
    app.state.authorization = authorization or AuthorizationService()
    app.state.entitlements = entitlements or EntitlementService()
    app.state.observability = observability or Observability.noop()
    register_exception_handlers(app)
    prefix = settings.api_prefix.rstrip("/")
    app.include_router(api_router, prefix=prefix)
    return app


app = create_app()
