from sqlalchemy import text

from nexo_vending.application.health import readiness


def test_sqlalchemy_connects_to_real_postgres(postgres_engine) -> None:
    with postgres_engine.connect() as connection:
        value = connection.execute(text("SELECT 1")).scalar_one()
    assert value == 1


def test_readiness_against_postgres(postgres_engine) -> None:
    payload = readiness(postgres_engine)
    assert payload["status"] == "ready"
    assert payload["api_version"] == "v1"
    assert "package_version" in payload
