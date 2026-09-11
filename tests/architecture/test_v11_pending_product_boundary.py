"""Architecture guards for V11 unresolved product / ledger integrity."""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_REPL = ROOT / "src" / "nexo_vending" / "domain" / "replenishment"
DOMAIN_INV = ROOT / "src" / "nexo_vending" / "domain" / "inventory"


def _imports_module(path: Path, forbidden: str) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == forbidden or alias.name.startswith(forbidden + "."):
                    return True
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == forbidden or node.module.startswith(forbidden + "."):
                return True
    return False


def test_domain_replenishment_does_not_import_fastapi() -> None:
    for path in DOMAIN_REPL.rglob("*.py"):
        assert not _imports_module(path, "fastapi"), path


def test_domain_replenishment_does_not_import_sqlalchemy() -> None:
    for path in DOMAIN_REPL.rglob("*.py"):
        assert not _imports_module(path, "sqlalchemy"), path


def test_inventory_movement_requires_product_id_in_domain() -> None:
    source = (DOMAIN_INV / "entities.py").read_text(encoding="utf-8")
    assert "product_id: ProductId" in source
    assert "product_id: ProductId | None" not in source
