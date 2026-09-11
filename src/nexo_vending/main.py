from fastapi import FastAPI
from nexo_platform.authorization import AuthorizationService
from nexo_platform.entitlement import EntitlementService
from nexo_platform.observability import Observability

from nexo_vending.api.error_handlers import register_exception_handlers
from nexo_vending.api.health import router as health_router
from nexo_vending.api.router import api_router
from nexo_vending.config import settings
from nexo_vending.versioning import API_PREFIX, API_VERSION, PACKAGE_VERSION


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
            f"Business routes are versioned under {API_PREFIX}. "
            "Inbound adapter over application use cases; uses Platform "
            "RequestContext, TransactionalUnitOfWork, Idempotency, and Observability."
        ),
        version=PACKAGE_VERSION,
    )
    app.state.authorization = authorization or AuthorizationService()
    app.state.entitlements = entitlements or EntitlementService()
    app.state.observability = observability or Observability.noop()
    register_exception_handlers(app)

    # Probes stay at process root (not under /api/v1).
    app.include_router(health_router)

    prefix = (settings.api_prefix or API_PREFIX).rstrip("/")
    app.include_router(api_router, prefix=prefix)
    app.state.api_prefix = prefix
    app.state.api_version = API_VERSION
    app.state.package_version = PACKAGE_VERSION
    return app


app = create_app()
