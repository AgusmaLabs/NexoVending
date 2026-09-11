from __future__ import annotations

import json
import subprocess
import time
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _run(*args: str, cwd: Path, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _http_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
        return json.loads(response.read().decode("utf-8"))


@pytest.mark.e2e
def test_docker_compose_runtime_smoke() -> None:
    # Ensure platform wheel exists for the Docker build context.
    _run(
        "python",
        str(ROOT / "scripts" / "vendor_platform.py"),
        cwd=ROOT,
        check=True,
    )

    compose = ["docker", "compose", "-f", str(ROOT / "docker-compose.yml")]
    _run(*compose, "down", "-v", cwd=ROOT)
    build = _run(*compose, "build", cwd=ROOT, check=True)
    assert build.returncode == 0, build.stderr

    up = _run(*compose, "up", "-d", cwd=ROOT, check=True)
    assert up.returncode == 0, up.stderr

    try:
        deadline = time.time() + 120
        ready_payload = None
        last_error = ""
        while time.time() < deadline:
            try:
                health = _http_json("http://127.0.0.1:8000/health")
                ready_payload = _http_json("http://127.0.0.1:8000/health/ready")
                if health.get("status") == "ok" and ready_payload.get("status") == "ready":
                    break
            except Exception as exc:  # noqa: BLE001 - retry until deadline
                last_error = str(exc)
                time.sleep(2)
        else:
            ps = _run(*compose, "ps", cwd=ROOT)
            logs = _run(*compose, "logs", "vending-api", cwd=ROOT)
            pytest.fail(
                "API did not become ready.\n"
                f"last_error={last_error}\nps={ps.stdout}\nlogs={logs.stdout}\n{logs.stderr}"
            )

        assert ready_payload["status"] == "ready"
        assert ready_payload["api_version"] == "v1"
        assert "package_version" in ready_payload
    finally:
        _run(*compose, "down", "-v", cwd=ROOT)
