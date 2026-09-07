from fastapi.testclient import TestClient

from nexo_vending.application.health import liveness
from nexo_vending.main import create_app


def test_liveness_payload() -> None:
    assert liveness() == {"status": "ok"}


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
