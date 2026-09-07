from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "nexo_vending"
DOMAIN_ROOT = SRC_ROOT / "domain"

FORBIDDEN_COPIED_PATHS = (
    ROOT / "nexo_platform",
    ROOT / "src" / "platform",
    ROOT / "src" / "platform_core",
    ROOT / "src" / "modules",
    ROOT / "src" / "products",
    ROOT / "modules" / "billing",
    ROOT / "modules" / "tenant",
    ROOT / "modules" / "identity",
)

# Public Platform surface allowed in Vending source.
ALLOWED_PLATFORM_PREFIXES = (
    "nexo_platform",
    "nexo_platform.authorization",
    "nexo_platform.billing",
    "nexo_platform.entitlement",
    "nexo_platform.events",
    "nexo_platform.identity",
    "nexo_platform.outbox",
    "nexo_platform.shared",
    "nexo_platform.tenant",
    "nexo_platform.transaction",
    "nexo_platform.usage",
)

FORBIDDEN_PLATFORM_PREFIXES = (
    "nexo_platform.infrastructure",
    "nexo_platform.modules",
    "nexo_platform.persistence",
    "nexo_platform.identity.infrastructure",
    "nexo_platform.tenant.infrastructure",
    "nexo_platform.billing.infrastructure",
    "nexo_platform.billing.domain",
    "nexo_platform.identity.domain",
    "nexo_platform.tenant.domain",
)

DOMAIN_FORBIDDEN = (
    "fastapi",
    "sqlalchemy",
    "alembic",
    "uvicorn",
    "psycopg",
    "nexo_platform",
    "nexo_vending.infrastructure",
    "nexo_vending.api",
)

APPLICATION_FORBIDDEN = (
    "nexo_vending.infrastructure",
)

PRODUCTS_ROOT = DOMAIN_ROOT / "products"
REPLENISHMENT_ROOT = DOMAIN_ROOT / "replenishment"


def python_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.py") if p.is_file())


def imported_names(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            names.append(node.module)
        elif isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
    return names


def starts_with_any(module: str, prefixes: Iterable[str]) -> bool:
    for prefix in prefixes:
        normalized = prefix.rstrip(".")
        if module == normalized or module.startswith(normalized + "."):
            return True
    return False


def is_allowed_platform_import(module: str) -> bool:
    if not module.startswith("nexo_platform"):
        return True
    if starts_with_any(module, FORBIDDEN_PLATFORM_PREFIXES):
        return False
    # Allow top-level package and explicit capability roots only.
    if module == "nexo_platform":
        return True
    return starts_with_any(module, ALLOWED_PLATFORM_PREFIXES)
