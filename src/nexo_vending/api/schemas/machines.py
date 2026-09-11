"""HTTP DTOs for machine resolution and slots."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MachineSlotOut(BaseModel):
    slot_id: str
    slot_number: int
    capacity: int
    status: str
    preferred_product_id: str | None = None
    selling_price: str | None = None
    current_quantity: int | None = None


class MachineOut(BaseModel):
    machine_id: str
    identifier: str
    machine_type: str
    name: str
    status: str
    slots: list[MachineSlotOut] = Field(default_factory=list)


class MachineSlotsOut(BaseModel):
    machine_id: str
    slots: list[MachineSlotOut] = Field(default_factory=list)
