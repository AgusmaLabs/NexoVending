from collections.abc import Iterator

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from nexo_vending.infrastructure.database import get_engine, get_session_factory


def get_db_engine() -> Engine:
    return get_engine()


def get_db_session() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
