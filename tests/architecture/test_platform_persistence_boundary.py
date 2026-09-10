"""Architecture: Vending uses public Platform persistence only."""

from nexo_platform.persistence import Database, SessionFactory

from tests.architecture._imports import (
    SRC_ROOT,
    imported_names,
    is_allowed_platform_import,
    python_files,
)


def test_public_persistence_imports_are_allowed() -> None:
    assert is_allowed_platform_import("nexo_platform.persistence")
    assert is_allowed_platform_import("nexo_platform.transaction")
    assert is_allowed_platform_import("nexo_platform.context")
    assert not is_allowed_platform_import("nexo_platform.persistence.database")
    assert not is_allowed_platform_import("nexo_platform.persistence.sqlalchemy")


def test_vending_does_not_import_persistence_internals() -> None:
    violations: list[str] = []
    for file in python_files(SRC_ROOT):
        for module in imported_names(file):
            if module.startswith("nexo_platform.persistence.") and module not in {
                "nexo_platform.persistence",
            }:
                violations.append(f"{file} imports {module}")
            if not is_allowed_platform_import(module):
                violations.append(f"{file} imports forbidden {module}")
    assert not violations, "\n".join(violations)


def test_database_public_symbols_exist() -> None:
    assert Database is not None
    assert SessionFactory is not None
