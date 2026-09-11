"""HTTP DTOs for inventory."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InventoryLocationIn(BaseModel):
    location_type: str
    holder_id: str
    position_id: str | None = None


class AssignInventoryRequest(BaseModel):
    product_id: str
    quantity: int
    replenisher_id: str
    reference_id: str
    administrator_id: str | None = None
    occurred_at: datetime | None = None


class ReturnInventoryRequest(BaseModel):
    product_id: str
    quantity: int
    replenisher_id: str
    administrator_id: str
    reference_id: str
    occurred_at: datetime | None = None


class AdjustInventoryRequest(BaseModel):
    product_id: str
    quantity: int
    location: InventoryLocationIn
    reference_id: str
    as_increase: bool = True
    occurred_at: datetime | None = None


class RecordLossRequest(BaseModel):
    product_id: str
    quantity: int
    location: InventoryLocationIn
    reference_id: str
    occurred_at: datetime | None = None


class InventoryLocationOut(BaseModel):
    location_type: str
    holder_id: str
    position_id: str | None = None


class InventoryMovementOut(BaseModel):
    id: str
    product_id: str
    quantity: int
    movement_type: str
    reference_type: str
    reference_id: str
    occurred_at: str
    actor_id: str
    source_location: InventoryLocationOut | None = None
    destination_location: InventoryLocationOut | None = None
    idempotency_key: str | None = None


class InventoryBalanceOut(BaseModel):
    quantity: int
    location: InventoryLocationOut
    product_id: str


class InventoryMovementsOut(BaseModel):
    items: list[InventoryMovementOut] = Field(default_factory=list)
