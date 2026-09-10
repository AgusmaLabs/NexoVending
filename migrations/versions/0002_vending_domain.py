"""vending domain persistence schema

Revision ID: 0002_vending_domain
Revises: 0001_vending_bootstrap
Create Date: 2026-09-10
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_vending_domain"
down_revision: str | Sequence[str] | None = "0001_vending_bootstrap"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "operators",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("principal_provider", sa.String(length=64), nullable=False),
        sa.Column("principal_subject", sa.String(length=256), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("display_name", sa.String(length=256), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "principal_provider",
            "principal_subject",
            name="uq_operators_tenant_principal",
        ),
    )
    op.create_index("ix_operators_tenant_id", "operators", ["tenant_id"])

    op.create_table(
        "products",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("barcode", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("unit", sa.String(length=32), nullable=False),
        sa.Column("low_stock_threshold", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("brand", sa.String(length=128), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "barcode", name="uq_products_tenant_barcode"),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    op.create_table(
        "machines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=256), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location_label", sa.String(length=256), nullable=True),
        sa.Column("location_latitude", sa.Numeric(12, 8), nullable=True),
        sa.Column("location_longitude", sa.Numeric(12, 8), nullable=True),
        sa.Column("sii_id", sa.String(length=128), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_machines_tenant_code"),
    )
    op.create_index("ix_machines_tenant_id", "machines", ["tenant_id"])

    op.create_table(
        "machine_slots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=False),
        sa.Column("slot_number", sa.Integer(), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("preferred_product_id", sa.Uuid(), nullable=True),
        sa.Column("selling_price_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("selling_price_currency", sa.String(length=8), nullable=True),
        sa.CheckConstraint("capacity > 0", name="ck_machine_slots_capacity_positive"),
        sa.CheckConstraint("slot_number > 0", name="ck_machine_slots_number_positive"),
        sa.ForeignKeyConstraint(["machine_id"], ["machines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("machine_id", "slot_number", name="uq_machine_slots_number"),
    )

    op.create_table(
        "replenishments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("machine_id", sa.Uuid(), nullable=False),
        sa.Column("machine_type", sa.String(length=32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("latitude", sa.Numeric(12, 8), nullable=False),
        sa.Column("longitude", sa.Numeric(12, 8), nullable=False),
        sa.Column("accuracy", sa.Numeric(12, 4), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_replenishments_tenant_idempotency",
        ),
    )
    op.create_index("ix_replenishments_tenant_id", "replenishments", ["tenant_id"])
    op.create_index("ix_replenishments_machine_id", "replenishments", ["machine_id"])

    op.create_table(
        "replenishment_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("replenishment_id", sa.Uuid(), nullable=False),
        sa.Column("machine_position_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("product_description_snapshot", sa.String(length=256), nullable=False),
        sa.Column("preferred_product_id_snapshot", sa.Uuid(), nullable=True),
        sa.Column("replacement_reason", sa.String(length=64), nullable=True),
        sa.Column("barcode_scanned", sa.String(length=64), nullable=True),
        sa.Column("manual_description", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["replenishment_id"], ["replenishments.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_replenishment_lines_replenishment_id",
        "replenishment_lines",
        ["replenishment_id"],
    )

    op.create_table(
        "inventory_movements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=32), nullable=False),
        sa.Column("reference_type", sa.String(length=32), nullable=False),
        sa.Column("reference_id", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("source_location_type", sa.String(length=32), nullable=True),
        sa.Column("source_holder_id", sa.String(length=64), nullable=True),
        sa.Column("source_position_id", sa.String(length=64), nullable=True),
        sa.Column("destination_location_type", sa.String(length=32), nullable=True),
        sa.Column("destination_holder_id", sa.String(length=64), nullable=True),
        sa.Column("destination_position_id", sa.String(length=64), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_inventory_movements_tenant_idempotency",
        "inventory_movements",
        ["tenant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("ix_inventory_movements_tenant_id", "inventory_movements", ["tenant_id"])
    op.create_index("ix_inventory_movements_product_id", "inventory_movements", ["product_id"])


def downgrade() -> None:
    op.drop_table("inventory_movements")
    op.drop_table("replenishment_lines")
    op.drop_table("replenishments")
    op.drop_table("machine_slots")
    op.drop_table("machines")
    op.drop_table("products")
    op.drop_table("operators")
