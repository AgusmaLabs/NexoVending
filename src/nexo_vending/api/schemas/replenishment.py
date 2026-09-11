"""HTTP DTOs for replenishment."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class GeoLocationIn(BaseModel):
    latitude: float
    longitude: float
    accuracy: float | None = None


class CreateReplenishmentRequest(BaseModel):
    machine_id: str
    location: GeoLocationIn
    started_at: datetime | None = None


class AddReplenishmentLineRequest(BaseModel):
    slot_id: str
    quantity: int
    product_id: str | None = None
    barcode: str | None = None
    manual_description: str | None = None
    replacement_reason: str | None = None
    unit_price: Decimal | None = None
    scanned_at: datetime | None = None


class CompleteReplenishmentRequest(BaseModel):
    completed_at: datetime | None = None


class CancelReplenishmentRequest(BaseModel):
    cancelled_at: datetime | None = None


class ReplenishmentLineOut(BaseModel):
    id: str
    slot_id: str
    product_id: str
    quantity: int
    unit_price: str
    occurred_at: str
    product_description_snapshot: str
    preferred_product_id_snapshot: str | None = None
    replacement_reason: str | None = None
    barcode_scanned: str | None = None
    manual_description: str | None = None


class ReplenishmentOut(BaseModel):
    id: str
    machine_id: str
    operator_id: str
    status: str
    machine_type: str
    started_at: str
    completed_at: str | None = None
    location: dict[str, float | None]
    idempotency_key: str
    version: int
    lines: list[ReplenishmentLineOut] = Field(default_factory=list)
