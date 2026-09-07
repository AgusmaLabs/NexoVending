from tests.architecture._imports import (
    DOMAIN_FORBIDDEN,
    DOMAIN_ROOT,
    imported_names,
    python_files,
    starts_with_any,
)


def test_domain_does_not_import_infrastructure_or_frameworks() -> None:
    violations: list[str] = []
    for file in python_files(DOMAIN_ROOT):
        for module in imported_names(file):
            if starts_with_any(module, DOMAIN_FORBIDDEN):
                violations.append(f"{file} imports {module}")
    assert not violations, "\n".join(violations)
