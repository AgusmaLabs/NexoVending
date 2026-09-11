"""Allow unresolved product lines; defer inventory until catalog resolve.

Revision ID: 0004_pending_product_resolution
Revises: 0003_machine_assignments
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_pending_product_resolution"
down_revision: str | Sequence[str] | None = "0003_machine_assignments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "replenishment_lines",
        sa.Column(
            "resolution_status",
            sa.String(length=64),
            nullable=False,
            server_default="resolved",
        ),
    )
    op.add_column(
        "replenishment_lines",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "replenishment_lines",
        sa.Column("resolved_by_operator_id", sa.Uuid(), nullable=True),
    )
    op.alter_column(
        "replenishment_lines",
        "product_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_replenishment_lines_resolution_product",
        "replenishment_lines",
        "(resolution_status = 'resolved' AND product_id IS NOT NULL) OR "
        "(resolution_status = 'pending_product_resolution' AND product_id IS NULL "
        "AND manual_description IS NOT NULL AND length(trim(manual_description)) > 0)",
    )
    op.create_index(
        "ix_replenishment_lines_resolution_status",
        "replenishment_lines",
        ["resolution_status"],
    )
    op.alter_column(
        "replenishment_lines",
        "resolution_status",
        server_default=None,
        existing_type=sa.String(length=64),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_replenishment_lines_resolution_status",
        table_name="replenishment_lines",
    )
    op.drop_constraint(
        "ck_replenishment_lines_resolution_product",
        "replenishment_lines",
        type_="check",
    )
    op.execute(
        "UPDATE replenishment_lines SET product_id = "
        "'00000000-0000-0000-0000-000000000000' WHERE product_id IS NULL"
    )
    op.alter_column(
        "replenishment_lines",
        "product_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("replenishment_lines", "resolved_by_operator_id")
    op.drop_column("replenishment_lines", "resolved_at")
    op.drop_column("replenishment_lines", "resolution_status")
