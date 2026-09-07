from tests.architecture._imports import FORBIDDEN_COPIED_PATHS


def test_repository_does_not_contain_copied_platform_trees() -> None:
    present = [str(path) for path in FORBIDDEN_COPIED_PATHS if path.exists()]
    assert not present, "copied Platform trees must not exist:\n" + "\n".join(present)
