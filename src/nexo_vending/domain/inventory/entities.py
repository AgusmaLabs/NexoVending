from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from nexo_vending.domain.common.errors import InvalidInventoryCountError
from nexo_vending.domain.common.ids import (
    InventoryCountId,
    InventoryMovementId,
    ProductId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Quantity, require_aware
from nexo_vending.domain.inventory.enums import (
    InventoryCountStatus,
    InventoryMovementType,
    InventoryReferenceType,
)
from nexo_vending.domain.inventory.locations import InventoryLocation


@dataclass(frozen=True, slots=True)
class InventoryMovement:
    """Immutable custody transfer / adjustment. Stock is derived from the ledger."""

    id: InventoryMovementId
    product_id: ProductId
    quantity: Quantity
    movement_type: InventoryMovementType
    reference_type: InventoryReferenceType
    reference_id: str
    occurred_at: datetime
    actor_id: UserId
    source_location: InventoryLocation | None = None
    destination_location: InventoryLocation | None = None

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field_name="occurred_at")
        ref = self.reference_id.strip()
        if not ref:
            raise ValueError("reference_id is required")
        object.__setattr__(self, "reference_id", ref)
        if self.source_location is None and self.destination_location is None:
            raise ValueError("movement requires source and/or destination location")
        if self.movement_type == InventoryMovementType.LOSS and self.destination_location is not None:
            raise ValueError("LOSS must not have a destination location")
        if self.movement_type == InventoryMovementType.SLOT_REMOVAL:
            if self.source_location is None or self.destination_location is None:
                raise ValueError("SLOT_REMOVAL requires source and destination")


@dataclass(frozen=True, slots=True)
class InventoryCountLine:
    product_id: ProductId
    expected_quantity: int
    physical_quantity: int

    def __post_init__(self) -> None:
        if self.expected_quantity < 0 or self.physical_quantity < 0:
            raise InvalidInventoryCountError("count quantities must be >= 0")

    @property
    def variance(self) -> int:
        return self.physical_quantity - self.expected_quantity


@dataclass(slots=True)
class InventoryCount:
    """Physical count for a custody or machine location. Does not mutate the ledger."""

    id: InventoryCountId
    location: InventoryLocation
    occurred_at: datetime
    actor_id: UserId
    status: InventoryCountStatus = InventoryCountStatus.IN_PROGRESS
    _lines: list[InventoryCountLine] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field_name="occurred_at")

    @property
    def lines(self) -> tuple[InventoryCountLine, ...]:
        return tuple(self._lines)

    @classmethod
    def create(
        cls,
        *,
        count_id: InventoryCountId,
        location: InventoryLocation,
        occurred_at: datetime,
        actor_id: UserId,
    ) -> InventoryCount:
        return cls(
            id=count_id,
            location=location,
            occurred_at=occurred_at,
            actor_id=actor_id,
        )

    def _ensure_in_progress(self) -> None:
        if self.status != InventoryCountStatus.IN_PROGRESS:
            raise InvalidInventoryCountError(
                f"cannot modify inventory count in status {self.status}"
            )

    def record_line(
        self,
        *,
        product_id: ProductId,
        expected_quantity: int,
        physical_quantity: int,
    ) -> InventoryCountLine:
        self._ensure_in_progress()
        line = InventoryCountLine(
            product_id=product_id,
            expected_quantity=expected_quantity,
            physical_quantity=physical_quantity,
        )
        self._lines = [existing for existing in self._lines if existing.product_id != product_id]
        self._lines.append(line)
        return line

    def complete(self) -> None:
        self._ensure_in_progress()
        self.status = InventoryCountStatus.COMPLETED

    def cancel(self) -> None:
        self._ensure_in_progress()
        self.status = InventoryCountStatus.CANCELLED
