"""Export OpenAPI JSON for mobile / frontend clients.

Usage (from repo root, with package installed):

    python scripts/export_openapi.py
    python scripts/export_openapi.py --out docs/api/openapi-v1.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write OpenAPI JSON to this path (stdout if omitted)",
    )
    args = parser.parse_args(argv)

    from nexo_vending.main import create_app
    from nexo_vending.versioning import API_PREFIX, API_VERSION, PACKAGE_VERSION

    schema = create_app().openapi()
    schema.setdefault("info", {})["x-nexo-api-version"] = API_VERSION
    schema["info"]["x-nexo-package-version"] = PACKAGE_VERSION
    schema["info"]["x-nexo-api-prefix"] = API_PREFIX

    payload = json.dumps(schema, indent=2, ensure_ascii=False) + "\n"
    if args.out is None:
        sys.stdout.write(payload)
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
        print(f"Wrote {args.out} (api={API_VERSION}, package={PACKAGE_VERSION})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
