"""Health and readiness application logic."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from nexo_vending.versioning import API_VERSION, PACKAGE_VERSION


def liveness() -> dict[str, str]:
    return {
        "status": "ok",
        "package_version": PACKAGE_VERSION,
        "api_version": API_VERSION,
    }


def readiness(engine: Engine) -> dict[str, str]:
    """Verify PostgreSQL connectivity for readiness probes."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise RuntimeError("database not ready") from exc
    return {
        "status": "ready",
        "package_version": PACKAGE_VERSION,
        "api_version": API_VERSION,
    }
