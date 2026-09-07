"""Concurrency policy for inventory (specification; persistence enforces it later)."""


def test_concurrency_is_persistence_concern_documented() -> None:
    """Domain exposes available quantity; lost-update prevention is persistence-owned.

    Example race:
      stock = 10
      consume 8
      consume 8

    Domain rule: resulting stock must not be negative.
    Persistence rule (future): serialize / lock / optimistic version so both
    consumptions cannot commit against the same ledger snapshot.
    """
    assert True
