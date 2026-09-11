from fastapi.testclient import TestClient

from nexo_vending.application.health import liveness
from nexo_vending.main import create_app
from nexo_vending.versioning import API_PREFIX, API_VERSION, PACKAGE_VERSION


def test_liveness_payload() -> None:
    assert liveness() == {
        "status": "ok",
        "package_version": PACKAGE_VERSION,
        "api_version": API_VERSION,
    }


def test_health_endpoint() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "package_version": PACKAGE_VERSION,
        "api_version": API_VERSION,
    }


def test_business_routes_are_under_api_v1() -> None:
    client = TestClient(create_app())
    paths = client.app.openapi()["paths"]
    assert "/health" in paths
    assert f"{API_PREFIX}/replenishments" in paths
    assert "/replenishments" not in paths
