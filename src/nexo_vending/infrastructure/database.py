"""Vending composition helpers around Platform public persistence.

Uses ``nexo_platform.persistence.Database`` / ``SessionFactory``.
Does not import Platform ORM ``Base`` or private ``persistence.database`` symbols.
"""

from __future__ import annotations

from collections.abc import Iterator

from nexo_platform.persistence import Database, SessionFactory
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from nexo_vending.config import settings

_db: Database | None = None


def get_database() -> Database:
    global _db
    if _db is None:
        _db = Database.from_url(settings.database_url)
    return _db


def get_engine() -> Engine:
    return get_database().engine


def get_session_factory() -> SessionFactory:
    return get_database().session_factory()


def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_engine() -> None:
    """Dispose the cached Database (tests / config reload)."""
    global _db
    if _db is not None:
        _db.dispose()
    _db = None
