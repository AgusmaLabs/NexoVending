from fastapi import FastAPI

from nexo_vending.api.router import api_router
from nexo_vending.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    prefix = settings.api_prefix.rstrip("/")
    app.include_router(api_router, prefix=prefix)
    return app


app = create_app()
