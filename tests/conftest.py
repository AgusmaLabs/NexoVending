"""Root test fixtures — PostgreSQL Testcontainers shared by integration and API."""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

postgres = pytest.importorskip("testcontainers.postgres")
PostgresContainer = postgres.PostgresContainer


def _docker_unavailable_reason(exc: BaseException) -> str:
    return (
        "PostgreSQL Testcontainers require a running Docker daemon "
        f"(or set TEST_DATABASE_URL). Original error: {exc}"
    )


@pytest.fixture(scope="session")
def postgres_url() -> str:
    if os.getenv("TEST_DATABASE_URL"):
        yield os.environ["TEST_DATABASE_URL"]
        return

    try:
        container = PostgresContainer("postgres:17")
        container.start()
    except Exception as exc:
        pytest.skip(_docker_unavailable_reason(exc))

    try:
        url = container.get_connection_url().replace(
            "postgresql+psycopg2", "postgresql+psycopg"
        )
        yield url
    finally:
        container.stop()


@pytest.fixture()
def postgres_engine(postgres_url: str) -> Engine:
    engine = create_engine(postgres_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        engine.dispose()
