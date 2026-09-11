from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[2]


def test_alembic_upgrade_and_downgrade(postgres_url: str) -> None:
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", postgres_url.replace("%", "%%"))

    command.upgrade(config, "head")

    engine = create_engine(postgres_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        assert version == "0003_machine_assignments"
    finally:
        engine.dispose()

    command.downgrade(config, "base")

    engine = create_engine(postgres_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            rows = connection.execute(text("SELECT version_num FROM alembic_version")).fetchall()
        assert rows == []
    finally:
        engine.dispose()
