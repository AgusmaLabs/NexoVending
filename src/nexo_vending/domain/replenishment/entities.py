from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidReplenishmentLineError,
    InvalidReplenishmentStateError,
)
from nexo_vending.domain.common.ids import (
    MachineId,
    ProductId,
    ReplenishmentId,
    UserId,
)
from nexo_vending.domain.common.value_objects import (
    Barcode,
    GeoLocation,
    Quantity,
    require_aware,
)
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.replenishment.enums import ReplenishmentStatus


@dataclass(frozen=True, slots=True)
class ReplenishmentLine:
    product_id: ProductId | None
    barcode_scanned: Barcode | None
    product_description_snapshot: str
    manual_description: str | None
    quantity: Quantity
    slot: int | None
    scanned_at: datetime

    def __post_init__(self) -> None:
        require_aware(self.scanned_at, field_name="scanned_at")
        snapshot = self.product_description_snapshot.strip()
        if not snapshot:
            raise InvalidReplenishmentLineError(
                "product_description_snapshot is required"
            )
        object.__setattr__(self, "product_description_snapshot", snapshot)

        manual = self.manual_description.strip() if self.manual_description else None
        if manual == "":
            manual = None
        object.__setattr__(self, "manual_description", manual)

        if self.product_id is None and manual is None:
            raise InvalidReplenishmentLineError(
                "unknown product requires manual_description"
            )


@dataclass(slots=True)
class Replenishment:
    """Aggregate root for a replenishment visit."""

    id: ReplenishmentId
    operator_id: UserId
    machine_id: MachineId
    machine_type: MachineType
    started_at: datetime
    location: GeoLocation
    idempotency_key: str
    status: ReplenishmentStatus = ReplenishmentStatus.IN_PROGRESS
    completed_at: datetime | None = None
    _lines: list[ReplenishmentLine] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        require_aware(self.started_at, field_name="started_at")
        key = self.idempotency_key.strip()
        if not key:
            raise InvalidReplenishmentStateError("idempotency_key is required")
        self.idempotency_key = key

    @property
    def lines(self) -> tuple[ReplenishmentLine, ...]:
        return tuple(self._lines)

    @classmethod
    def start(
        cls,
        *,
        replenishment_id: ReplenishmentId,
        operator_id: UserId,
        machine: Machine,
        started_at: datetime,
        location: GeoLocation,
        idempotency_key: str,
    ) -> Replenishment:
        if not machine.active:
            raise InactiveMachineError("inactive machine cannot start replenishment")
        machine.ensure_can_start_replenishment()
        return cls(
            id=replenishment_id,
            operator_id=operator_id,
            machine_id=machine.id,
            machine_type=machine.type,
            started_at=started_at,
            location=location,
            idempotency_key=idempotency_key,
            status=ReplenishmentStatus.IN_PROGRESS,
        )

    def _ensure_in_progress(self) -> None:
        if self.status != ReplenishmentStatus.IN_PROGRESS:
            raise InvalidReplenishmentStateError(
                f"cannot modify replenishment in status {self.status}"
            )

    def add_line(
        self,
        *,
        product_id: ProductId | None,
        barcode_scanned: Barcode | None,
        product_description_snapshot: str,
        manual_description: str | None,
        quantity: Quantity,
        slot: int | None,
        scanned_at: datetime,
    ) -> ReplenishmentLine:
        self._ensure_in_progress()

        if self.machine_type == MachineType.SNACK:
            if slot is None:
                raise InvalidReplenishmentLineError("snack replenishment requires slot")
            if slot <= 0:
                raise InvalidReplenishmentLineError("slot must be > 0")
        elif self.machine_type == MachineType.COFFEE:
            if slot is not None:
                raise InvalidReplenishmentLineError("coffee replenishment does not use slot")

        if product_id is not None and manual_description and manual_description.strip():
            # Known products may still carry optional notes, but snapshot is authoritative.
            pass

        line = ReplenishmentLine(
            product_id=product_id,
            barcode_scanned=barcode_scanned,
            product_description_snapshot=product_description_snapshot,
            manual_description=manual_description,
            quantity=quantity,
            slot=slot,
            scanned_at=scanned_at,
        )
        self._lines.append(line)
        return line

    def complete(self, *, completed_at: datetime) -> None:
        self._ensure_in_progress()
        require_aware(completed_at, field_name="completed_at")
        self.status = ReplenishmentStatus.COMPLETED
        self.completed_at = completed_at

    def cancel(self, *, cancelled_at: datetime | None = None) -> None:
        self._ensure_in_progress()
        if cancelled_at is not None:
            require_aware(cancelled_at, field_name="cancelled_at")
        self.status = ReplenishmentStatus.CANCELLED
        self.completed_at = cancelled_at
