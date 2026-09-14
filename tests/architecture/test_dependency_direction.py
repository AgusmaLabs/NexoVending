from tests.architecture._imports import (
    ROOT,
    SRC_ROOT,
    imported_names,
    is_allowed_platform_import,
    python_files,
    starts_with_any,
)


def test_vending_may_depend_on_platform() -> None:
    import nexo_platform

    import nexo_vending

    assert nexo_vending.__version__
    assert nexo_platform.Tenant is not None
    assert nexo_platform.UnitOfWork is not None
    assert nexo_platform.TransactionalUnitOfWork is not None
    assert nexo_platform.Database is not None
    assert nexo_platform.DomainEvent is not None


def test_platform_source_tree_does_not_import_vending() -> None:
    """Conceptual rule: Platform must never depend on Vending.

    Platform lives in another repository; if its sources are present beside this
    checkout (local sibling), assert the direction. Otherwise the package
    import graph still proves Vending → Platform only.
    """
    sibling = ROOT.parent / "NexoPlatform" / "nexo_platform"
    if not sibling.exists():
        import nexo_platform

        assert "nexo_vending" not in getattr(nexo_platform, "__all__", ())
        return

    violations: list[str] = []
    for file in python_files(sibling):
        for module in imported_names(file):
            if starts_with_any(module, ("nexo_vending",)):
                violations.append(f"{file} imports {module}")
    assert not violations, "\n".join(violations)


def test_vending_source_does_not_use_platform_internals() -> None:
    violations: list[str] = []
    for file in python_files(SRC_ROOT):
        for module in imported_names(file):
            if not is_allowed_platform_import(module, path=file):
                violations.append(f"{file} imports forbidden {module}")
    assert not violations, "\n".join(violations)
