"""Vending bootstrap revision.

No domain tables yet — establishes an independent Alembic chain for Vending.
"""

from collections.abc import Sequence

revision: str = "0001_vending_bootstrap"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Intentionally empty: V01 validates migrations without inventing domain tables.
    pass


def downgrade() -> None:
    pass
