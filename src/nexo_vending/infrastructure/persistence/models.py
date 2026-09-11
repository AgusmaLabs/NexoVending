"""SQLAlchemy ORM models for NexoVending domain persistence."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nexo_vending.infrastructure.persistence.base import Base


class OperatorORM(Base):
    __tablename__ = "operators"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "principal_provider",
            "principal_subject",
            name="uq_operators_tenant_principal",
        ),
        Index("ix_operators_tenant_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_provider: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_subject: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProductORM(Base):
    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("tenant_id", "barcode", name="uq_products_tenant_barcode"),
        Index("ix_products_tenant_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    barcode: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    category: Mapped[str | None] = mapped_column(String(128), nullable=True)


class MachineORM(Base):
    __tablename__ = "machines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_machines_tenant_code"),
        Index("ix_machines_tenant_id", "tenant_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    location_latitude: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    location_longitude: Mapped[float | None] = mapped_column(Numeric(12, 8), nullable=True)
    sii_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    slots: Mapped[list[MachineSlotORM]] = relationship(
        back_populates="machine",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class MachineSlotORM(Base):
    __tablename__ = "machine_slots"
    __table_args__ = (
        UniqueConstraint("machine_id", "slot_number", name="uq_machine_slots_number"),
        CheckConstraint("capacity > 0", name="ck_machine_slots_capacity_positive"),
        CheckConstraint("slot_number > 0", name="ck_machine_slots_number_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    machine_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
    )
    slot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    preferred_product_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    selling_price_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    selling_price_currency: Mapped[str | None] = mapped_column(String(8), nullable=True)

    machine: Mapped[MachineORM] = relationship(back_populates="slots")


class ReplenishmentORM(Base):
    __tablename__ = "replenishments"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "idempotency_key",
            name="uq_replenishments_tenant_idempotency",
        ),
        Index("ix_replenishments_tenant_id", "tenant_id"),
        Index("ix_replenishments_machine_id", "machine_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    operator_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    machine_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    machine_type: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    latitude: Mapped[float] = mapped_column(Numeric(12, 8), nullable=False)
    longitude: Mapped[float] = mapped_column(Numeric(12, 8), nullable=False)
    accuracy: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    lines: Mapped[list[ReplenishmentLineORM]] = relationship(
        back_populates="replenishment",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReplenishmentLineORM(Base):
    __tablename__ = "replenishment_lines"
    __table_args__ = (
        Index("ix_replenishment_lines_replenishment_id", "replenishment_id"),
        Index("ix_replenishment_lines_resolution_status", "resolution_status"),
        CheckConstraint(
            "(resolution_status = 'resolved' AND product_id IS NOT NULL) OR "
            "(resolution_status = 'pending_product_resolution' AND product_id IS NULL "
            "AND manual_description IS NOT NULL AND length(trim(manual_description)) > 0)",
            name="ck_replenishment_lines_resolution_product",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    replenishment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("replenishments.id", ondelete="CASCADE"),
        nullable=False,
    )
    machine_position_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    product_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    product_description_snapshot: Mapped[str] = mapped_column(String(256), nullable=False)
    preferred_product_id_snapshot: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    replacement_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    barcode_scanned: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manual_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_status: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by_operator_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    replenishment: Mapped[ReplenishmentORM] = relationship(back_populates="lines")


class InventoryMovementORM(Base):
    __tablename__ = "inventory_movements"
    __table_args__ = (
        Index(
            "uq_inventory_movements_tenant_idempotency",
            "tenant_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        CheckConstraint("quantity > 0", name="ck_inventory_movements_quantity_positive"),
        Index("ix_inventory_movements_tenant_id", "tenant_id"),
        Index("ix_inventory_movements_product_id", "product_id"),
        Index(
            "ix_inventory_movements_source",
            "source_location_type",
            "source_holder_id",
            "source_position_id",
        ),
        Index(
            "ix_inventory_movements_destination",
            "destination_location_type",
            "destination_holder_id",
            "destination_position_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    product_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    movement_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(32), nullable=False)
    reference_id: Mapped[str] = mapped_column(String(128), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    source_location_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_holder_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_position_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination_location_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    destination_holder_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    destination_position_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)


class MachineAssignmentORM(Base):
    __tablename__ = "machine_assignments"
    __table_args__ = (
        Index("ix_machine_assignments_tenant_id", "tenant_id"),
        Index(
            "ix_machine_assignments_lookup",
            "tenant_id",
            "replenisher_id",
            "machine_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "replenisher_id",
            "machine_id",
            "valid_from",
            name="uq_machine_assignments_active_window",
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    replenisher_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    machine_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    valid_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
