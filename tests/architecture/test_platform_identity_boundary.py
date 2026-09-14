from importlib.metadata import version

from nexo_platform.identity.authentication import (
    AuthenticatedIdentity,
    AuthenticationResult,
    ExternalIdentity,
    Principal,
)

from tests.architecture._imports import (
    COMPOSITION_ROOT_AUTH_PROVIDERS,
    ROOT,
    SRC_ROOT,
    imported_names,
    python_files,
    starts_with_any,
)

FORBIDDEN_AUTH_LIBS = (
    "google.oauth2",
    "google.auth",
    "authlib",
    "jose",
    "python_jose",
)


def test_consumes_nexo_platform_1_11_0() -> None:
    assert version("nexo-platform") == "1.11.0"


def test_platform_auth_types_come_from_nexo_platform_package() -> None:
    for cls in (Principal, AuthenticatedIdentity, ExternalIdentity, AuthenticationResult):
        assert cls.__module__.startswith("nexo_platform."), cls.__module__


def test_vending_does_not_implement_local_oauth_or_jwt() -> None:
    forbidden_names = ("google", "oauth", "jwt")
    offenders: list[str] = []
    for path in python_files(SRC_ROOT):
        name = path.name.lower()
        if any(token in name for token in forbidden_names):
            offenders.append(str(path.relative_to(ROOT)))
    assert not offenders, "local auth implementations are forbidden:\n" + "\n".join(offenders)


def test_vending_does_not_import_provider_sdks() -> None:
    violations: list[str] = []
    for path in python_files(SRC_ROOT):
        for module in imported_names(path):
            if starts_with_any(module, FORBIDDEN_AUTH_LIBS):
                violations.append(f"{path} imports {module}")
    assert not violations, "\n".join(violations)


def test_google_oauth_provider_import_only_in_composition_root() -> None:
    offenders: list[str] = []
    for path in python_files(SRC_ROOT):
        for module in imported_names(path):
            if starts_with_any(module, ("nexo_platform.identity.infrastructure",)):
                if path.resolve() != COMPOSITION_ROOT_AUTH_PROVIDERS:
                    offenders.append(f"{path} imports {module}")
    assert not offenders, "\n".join(offenders)


def test_no_copied_platform_identity_tree() -> None:
    assert not (ROOT / "nexo_platform" / "identity").exists()
    assert not (SRC_ROOT / "identity" / "oauth").exists()
