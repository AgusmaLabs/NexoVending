"""HTTP API and package versioning invariants."""

from fastapi.testclient import TestClient

from nexo_vending import __version__
from nexo_vending.main import create_app
from nexo_vending.versioning import API_PREFIX, API_VERSION, PACKAGE_VERSION


def test_package_version_is_single_source() -> None:
    assert __version__ == PACKAGE_VERSION == "0.2.0"


def test_openapi_reports_package_version_and_v1_prefix() -> None:
    app = create_app()
    client = TestClient(app)
    schema = client.get("/openapi.json").json()
    assert schema["info"]["version"] == PACKAGE_VERSION
    assert API_VERSION == "v1"
    assert API_PREFIX == "/api/v1"
    assert any(path.startswith(API_PREFIX) for path in schema["paths"])
    assert app.state.api_prefix == API_PREFIX
