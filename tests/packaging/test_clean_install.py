from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

pytestmark = pytest.mark.packaging


def _python_in_venv(venv: Path) -> Path:
    if sys.platform == "win32":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def _ensure_platform_wheel(vendor: Path) -> Path:
    vendor.mkdir(parents=True, exist_ok=True)
    wheels = list(vendor.glob("nexo_platform-*.whl"))
    if wheels:
        return wheels[0]

    platform_root = Path(
        __import__("os").environ.get("NEXO_PLATFORM_PATH", str(ROOT.parent / "NexoPlatform"))
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "vendor_platform.py"), "--platform-root", str(platform_root)],
        check=True,
        cwd=ROOT,
    )
    wheels = list(vendor.glob("nexo_platform-*.whl"))
    assert wheels, "expected nexo_platform wheel in vendor/"
    return wheels[0]


def test_wheel_installs_and_imports_in_clean_venv(tmp_path: Path) -> None:
    vendor = ROOT / "vendor"
    platform_wheel = _ensure_platform_wheel(vendor)

    dist = tmp_path / "dist"
    dist.mkdir()
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
    )
    wheels = list(dist.glob("nexo_vending-*.whl"))
    assert wheels, f"expected nexo_vending wheel in {dist}"

    venv = tmp_path / "clean-env"
    subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
    python = _python_in_venv(venv)
    subprocess.run([str(python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--find-links",
            str(vendor),
            str(platform_wheel),
            str(wheels[0]),
        ],
        check=True,
    )
    subprocess.run(
        [
            str(python),
            "-c",
            "import nexo_platform, nexo_vending, nexo_vending.domain; "
            "from importlib.metadata import version; "
            "from nexo_platform import DomainEvent, Tenant, UnitOfWork, "
            "TransactionalUnitOfWork, Database; "
            "from nexo_platform.identity.authentication import Principal; "
            "from nexo_vending.domain.replenishment import Replenishment; "
            "from nexo_vending.domain.inventory import InventoryLedger; "
            "from nexo_vending.domain.identity import Operator; "
            "assert version('nexo-platform') == '1.10.0'; "
            "assert nexo_vending.__version__; assert Tenant; assert UnitOfWork; "
            "assert TransactionalUnitOfWork is not None; assert Database is not None; "
            "assert DomainEvent(event_type='ok').event_type == 'ok'; "
            "assert Principal.__module__.startswith('nexo_platform.'); "
            "assert Replenishment is not None; assert InventoryLedger is not None; "
            "assert Operator is not None",
        ],
        check=True,
    )
