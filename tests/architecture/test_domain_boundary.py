from tests.architecture._imports import (
    APPLICATION_FORBIDDEN,
    DOMAIN_ROOT,
    PRODUCTS_ROOT,
    REPLENISHMENT_ROOT,
    SRC_ROOT,
    imported_names,
    is_forbidden_domain_import,
    python_files,
    starts_with_any,
)

APPLICATION_ROOT = SRC_ROOT / "application"


def test_domain_does_not_import_infrastructure_frameworks_or_platform() -> None:
    violations: list[str] = []
    for file in python_files(DOMAIN_ROOT):
        for module in imported_names(file):
            if is_forbidden_domain_import(file, module):
                violations.append(f"{file} imports {module}")
    assert not violations, "\n".join(violations)


def test_application_does_not_import_infrastructure_package() -> None:
    violations: list[str] = []
    for file in python_files(APPLICATION_ROOT):
        for module in imported_names(file):
            if starts_with_any(module, APPLICATION_FORBIDDEN):
                violations.append(f"{file} imports {module}")
    assert not violations, "\n".join(violations)


def test_products_module_does_not_depend_on_replenishment() -> None:
    violations: list[str] = []
    for file in python_files(PRODUCTS_ROOT):
        for module in imported_names(file):
            if starts_with_any(module, ("nexo_vending.domain.replenishment",)):
                violations.append(f"{file} imports {module}")
    assert not violations, "\n".join(violations)


def test_replenishment_module_exists() -> None:
    assert any(python_files(REPLENISHMENT_ROOT))
