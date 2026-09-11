"""Database dependencies for the HTTP adapter."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Request
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from nexo_vending.infrastructure.database import get_engine, get_session_factory


def get_db_engine() -> Engine:
    return get_engine()


def get_db_session(request: Request) -> Iterator[Session]:
    factory = getattr(request.app.state, "session_factory", None) or get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()
