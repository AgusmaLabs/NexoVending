"""Architecture rules for the HTTP inbound adapter (V9)."""

from tests.architecture._imports import (
    SRC_ROOT,
    imported_names,
    is_allowed_platform_import,
    python_files,
    starts_with_any,
)

API_ROOT = SRC_ROOT / "api"
ROUTERS_ROOT = API_ROOT / "routers"
APPLICATION_ROOT = SRC_ROOT / "application"
DOMAIN_ROOT = SRC_ROOT / "domain"


def test_domain_does_not_import_fastapi_or_api() -> None:
    violations: list[str] = []
    for path in python_files(DOMAIN_ROOT):
        for module in imported_names(path):
            if starts_with_any(module, ("fastapi", "nexo_vending.api")):
                violations.append(f"{path} imports {module}")
    assert not violations, "\n".join(violations)


def test_application_does_not_import_fastapi() -> None:
    violations: list[str] = []
    for path in python_files(APPLICATION_ROOT):
        for module in imported_names(path):
            if starts_with_any(module, ("fastapi",)):
                violations.append(f"{path} imports {module}")
    assert not violations, "\n".join(violations)


def test_routers_do_not_import_sqlalchemy_repositories() -> None:
    forbidden = (
        "nexo_vending.infrastructure.persistence.repositories",
        "nexo_vending.infrastructure.persistence.models",
    )
    violations: list[str] = []
    for path in python_files(ROUTERS_ROOT):
        for module in imported_names(path):
            if starts_with_any(module, forbidden) or "SqlAlchemy" in module:
                violations.append(f"{path} imports {module}")
    assert not violations, "\n".join(violations)


def test_api_platform_imports_are_public_only() -> None:
    violations: list[str] = []
    for path in python_files(API_ROOT):
        for module in imported_names(path):
            if module.startswith("nexo_platform") and not is_allowed_platform_import(module):
                violations.append(f"{path} imports {module}")
    assert not violations, "\n".join(violations)
