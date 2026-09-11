"""HTTP DTOs for product lookup."""

from __future__ import annotations

from pydantic import BaseModel


class ProductOut(BaseModel):
    product_id: str
    barcode: str
    name: str
    status: str
    unit: str
