"""Add machine_assignments for replenisher operational access.

Revision ID: 0003_machine_assignments
Revises: 0002_vending_domain
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_machine_assignments"
down_revision: str | Sequence[str] | None = "0002_vending_domain"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "machine_assignments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("replenisher_id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "replenisher_id",
            "machine_id",
            "valid_from",
            name="uq_machine_assignments_active_window",
        ),
    )
    op.create_index("ix_machine_assignments_tenant_id", "machine_assignments", ["tenant_id"])
    op.create_index(
        "ix_machine_assignments_lookup",
        "machine_assignments",
        ["tenant_id", "replenisher_id", "machine_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_machine_assignments_lookup", table_name="machine_assignments")
    op.drop_index("ix_machine_assignments_tenant_id", table_name="machine_assignments")
    op.drop_table("machine_assignments")
