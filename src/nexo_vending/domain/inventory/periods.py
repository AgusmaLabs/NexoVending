from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import InvalidMachineInventoryError
from nexo_vending.domain.common.ids import (
    MachineId,
    MachineInventoryPeriodId,
    SlotId,
)
from nexo_vending.domain.common.value_objects import require_aware


@dataclass(slots=True)
class MachineInventoryPeriod:
    """Machine/slot inventory window. Opening is a period condition, not a movement."""

    id: MachineInventoryPeriodId
    machine_id: MachineId
    position_id: SlotId
    opened_at: datetime
    opening_quantity: int = 0
    physical_quantity: int | None = None
    closed_at: datetime | None = None
    replenishment_net: int = 0
    consumption: int = 0

    def __post_init__(self) -> None:
        require_aware(self.opened_at, field_name="opened_at")
        if self.opening_quantity < 0:
            raise InvalidMachineInventoryError("opening_quantity must be >= 0")
        if self.closed_at is not None:
            require_aware(self.closed_at, field_name="closed_at")

    @classmethod
    def open_initial(
        cls,
        *,
        period_id: MachineInventoryPeriodId,
        machine_id: MachineId,
        position_id: SlotId,
        opened_at: datetime,
    ) -> MachineInventoryPeriod:
        return cls(
            id=period_id,
            machine_id=machine_id,
            position_id=position_id,
            opened_at=opened_at,
            opening_quantity=0,
        )

    @property
    def is_open(self) -> bool:
        return self.closed_at is None

    @property
    def theoretical_quantity(self) -> int:
        return self.opening_quantity + self.replenishment_net - self.consumption

    @property
    def variance(self) -> int | None:
        if self.physical_quantity is None:
            return None
        return self.physical_quantity - self.theoretical_quantity

    def apply_replenishment(self, signed_quantity: int) -> None:
        self._ensure_open()
        if signed_quantity == 0:
            raise InvalidMachineInventoryError("replenishment quantity must not be 0")
        self.replenishment_net += signed_quantity

    def apply_consumption(self, quantity: int) -> None:
        self._ensure_open()
        if quantity <= 0:
            raise InvalidMachineInventoryError("consumption must be > 0")
        self.consumption += quantity

    def record_physical_count(self, physical_quantity: int) -> int:
        self._ensure_open()
        if physical_quantity < 0:
            raise InvalidMachineInventoryError("physical_quantity must be >= 0")
        self.physical_quantity = physical_quantity
        return self.variance if self.variance is not None else 0

    def close(self, *, closed_at: datetime) -> MachineInventoryPeriod:
        self._ensure_open()
        require_aware(closed_at, field_name="closed_at")
        if self.physical_quantity is None:
            raise InvalidMachineInventoryError(
                "physical count is required before closing a period"
            )
        self.closed_at = closed_at
        return self

    def open_next(
        self,
        *,
        period_id: MachineInventoryPeriodId,
        opened_at: datetime,
    ) -> MachineInventoryPeriod:
        if self.is_open:
            raise InvalidMachineInventoryError("current period must be closed first")
        assert self.physical_quantity is not None
        return MachineInventoryPeriod(
            id=period_id,
            machine_id=self.machine_id,
            position_id=self.position_id,
            opened_at=opened_at,
            opening_quantity=self.physical_quantity,
        )

    def _ensure_open(self) -> None:
        if not self.is_open:
            raise InvalidMachineInventoryError("period is already closed")
