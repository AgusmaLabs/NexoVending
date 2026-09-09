from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nexo_vending.domain.common.errors import InvalidThresholdError
from nexo_vending.domain.common.ids import ProductId, TenantId
from nexo_vending.domain.common.value_objects import Barcode, require_aware
from nexo_vending.domain.products.enums import ProductStatus, ProductUnit
from nexo_vending.domain.products.errors import (
    InvalidProductStateError,
    ProductError,
)
from nexo_vending.domain.products.value_objects import ProductName, normalize_optional_text


@dataclass(slots=True)
class Product:
    """Tenant-scoped product catalog aggregate root."""

    id: ProductId
    tenant_id: TenantId
    barcode: Barcode
    name: ProductName
    unit: ProductUnit
    low_stock_threshold: int
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
    description: str | None = None
    brand: str | None = None
    category: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            raise ProductError("product requires tenant_id")
        if not isinstance(self.barcode, Barcode):
            raise ProductError("product requires barcode")
        if not isinstance(self.name, ProductName):
            if isinstance(self.name, str):
                self.name = ProductName(self.name)
            else:
                raise ProductError("product requires name")
        if not isinstance(self.unit, ProductUnit):
            raise ProductError("product requires valid unit")
        if not isinstance(self.status, ProductStatus):
            raise ProductError("product requires valid status")
        if self.low_stock_threshold < 0:
            raise InvalidThresholdError("low_stock_threshold must be >= 0")
        require_aware(self.created_at, field_name="created_at")
        require_aware(self.updated_at, field_name="updated_at")
        self.description = normalize_optional_text(
            self.description, field_name="description"
        )
        self.brand = normalize_optional_text(self.brand, field_name="brand")
        self.category = normalize_optional_text(self.category, field_name="category")

    @classmethod
    def create(
        cls,
        *,
        product_id: ProductId,
        tenant_id: TenantId,
        barcode: Barcode,
        name: str | ProductName,
        unit: ProductUnit = ProductUnit.UNIT,
        low_stock_threshold: int = 0,
        description: str | None = None,
        brand: str | None = None,
        category: str | None = None,
        created_at: datetime | None = None,
    ) -> Product:
        now = created_at or datetime.now(UTC)
        product_name = name if isinstance(name, ProductName) else ProductName(name)
        return cls(
            id=product_id,
            tenant_id=tenant_id,
            barcode=barcode,
            name=product_name,
            unit=unit,
            low_stock_threshold=low_stock_threshold,
            status=ProductStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            description=description,
            brand=brand,
            category=category,
        )

    @property
    def display_name(self) -> str:
        return self.name.value

    def update_details(
        self,
        *,
        name: str | ProductName,
        description: str | None,
        brand: str | None,
        category: str | None,
        unit: ProductUnit,
        low_stock_threshold: int,
        updated_at: datetime | None = None,
    ) -> None:
        self.name = name if isinstance(name, ProductName) else ProductName(name)
        if not isinstance(unit, ProductUnit):
            raise ProductError("product requires valid unit")
        if low_stock_threshold < 0:
            raise InvalidThresholdError("low_stock_threshold must be >= 0")
        self.description = normalize_optional_text(description, field_name="description")
        self.brand = normalize_optional_text(brand, field_name="brand")
        self.category = normalize_optional_text(category, field_name="category")
        self.unit = unit
        self.low_stock_threshold = low_stock_threshold
        self.updated_at = updated_at or datetime.now(UTC)
        require_aware(self.updated_at, field_name="updated_at")

    def change_barcode(self, barcode: Barcode, *, updated_at: datetime | None = None) -> None:
        self.barcode = barcode
        self.updated_at = updated_at or datetime.now(UTC)
        require_aware(self.updated_at, field_name="updated_at")

    def activate(self, *, updated_at: datetime | None = None) -> None:
        if self.status == ProductStatus.ACTIVE:
            return
        if self.status != ProductStatus.INACTIVE:
            raise InvalidProductStateError(
                f"cannot activate product from status {self.status}"
            )
        self.status = ProductStatus.ACTIVE
        self.updated_at = updated_at or datetime.now(UTC)

    def deactivate(self, *, updated_at: datetime | None = None) -> None:
        if self.status == ProductStatus.INACTIVE:
            return
        if self.status != ProductStatus.ACTIVE:
            raise InvalidProductStateError(
                f"cannot deactivate product from status {self.status}"
            )
        self.status = ProductStatus.INACTIVE
        self.updated_at = updated_at or datetime.now(UTC)
