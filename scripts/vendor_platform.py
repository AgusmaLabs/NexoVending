"""Build a nexo-platform wheel into ./vendor for offline / Docker installs.

Usage:
  python scripts/vendor_platform.py
  python scripts/vendor_platform.py --platform-root ../NexoPlatform
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLATFORM_ROOT = ROOT.parent / "NexoPlatform"
VENDOR = ROOT / "vendor"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--platform-root",
        type=Path,
        default=Path(
            __import__("os").environ.get("NEXO_PLATFORM_PATH", str(DEFAULT_PLATFORM_ROOT))
        ),
        help="Path to the NexoPlatform repository (default: ../NexoPlatform or NEXO_PLATFORM_PATH)",
    )
    args = parser.parse_args()
    platform_root: Path = args.platform_root.resolve()

    if not (platform_root / "pyproject.toml").exists():
        print(f"NexoPlatform not found at {platform_root}", file=sys.stderr)
        print("Set --platform-root or NEXO_PLATFORM_PATH.", file=sys.stderr)
        return 1

    VENDOR.mkdir(parents=True, exist_ok=True)
    for old in VENDOR.glob("nexo_platform-*.whl"):
        old.unlink()

    dist = VENDOR / "_platform_dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "build"],
        check=True,
    )
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=platform_root,
        check=True,
    )

    wheels = list(dist.glob("nexo_platform-*.whl"))
    if not wheels:
        print("No nexo_platform wheel produced", file=sys.stderr)
        return 1

    target = VENDOR / wheels[0].name
    shutil.copy2(wheels[0], target)
    shutil.rmtree(dist)
    print(f"Vendored {target.name} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
