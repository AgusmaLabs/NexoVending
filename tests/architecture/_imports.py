from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src" / "nexo_vending"
DOMAIN_ROOT = SRC_ROOT / "domain"
IDENTITY_ROOT = DOMAIN_ROOT / "identity"

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

# Public Platform surface allowed in Vending source (nexo-platform 1.7.0+).
ALLOWED_PLATFORM_PREFIXES = (
    "nexo_platform",
    "nexo_platform.authorization",
    "nexo_platform.billing",
    "nexo_platform.context",
    "nexo_platform.entitlement",
    "nexo_platform.events",
    "nexo_platform.identity",
    "nexo_platform.identity.authentication",
    "nexo_platform.outbox",
    "nexo_platform.persistence",
    "nexo_platform.shared",
    "nexo_platform.tenant",
    "nexo_platform.transaction",
    "nexo_platform.usage",
)

FORBIDDEN_PLATFORM_PREFIXES = (
    "nexo_platform.infrastructure",
    "nexo_platform.modules",
    # Public: nexo_platform.persistence (Database, SessionFactory).
    # Private: module internals and SQLAlchemy adapters.
    "nexo_platform.persistence.database",
    "nexo_platform.persistence.sqlalchemy",
    "nexo_platform.identity.infrastructure",
    "nexo_platform.tenant.infrastructure",
    "nexo_platform.billing.infrastructure",
    "nexo_platform.billing.domain",
    "nexo_platform.identity.domain",
    "nexo_platform.tenant.domain",
)

DOMAIN_FORBIDDEN_BASE = (
    "fastapi",
    "sqlalchemy",
    "alembic",
    "uvicorn",
    "psycopg",
    "nexo_vending.infrastructure",
    "nexo_vending.api",
    "google",
    "google.oauth2",
    "google.auth",
    "authlib",
    "jose",
    "python_jose",
)

# Only domain.identity may bind Platform authentication contracts (Principal).
DOMAIN_ALLOWED_PLATFORM_IN_IDENTITY = (
    "nexo_platform.identity.authentication",
)

APPLICATION_FORBIDDEN = (
    "nexo_vending.infrastructure",
    "google.oauth2",
    "google.auth",
    "authlib",
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
    if module == "nexo_platform":
        return True
    return starts_with_any(module, ALLOWED_PLATFORM_PREFIXES)


def is_forbidden_domain_import(path: Path, module: str) -> bool:
    if starts_with_any(module, DOMAIN_FORBIDDEN_BASE):
        return True
    if not module.startswith("nexo_platform"):
        return False
    try:
        path.relative_to(IDENTITY_ROOT)
        in_identity = True
    except ValueError:
        in_identity = False
    if in_identity and starts_with_any(module, DOMAIN_ALLOWED_PLATFORM_IN_IDENTITY):
        return False
    return True
