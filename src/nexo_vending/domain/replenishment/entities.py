from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidReplenishmentLineError,
    InvalidReplenishmentStateError,
)
from nexo_vending.domain.common.ids import (
    MachineId,
    ProductId,
    ReplenishmentId,
    ReplenishmentLineId,
    SlotId,
    TenantId,
    UserId,
)
from nexo_vending.domain.common.value_objects import (
    Barcode,
    GeoLocation,
    SignedQuantity,
    require_aware,
)
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.replenishment.capacity import validate_operation_capacity
from nexo_vending.domain.replenishment.enums import (
    ReplacementReason,
    ReplenishmentStatus,
)
from nexo_vending.domain.replenishment.substitution import resolve_substitution


@dataclass(frozen=True, slots=True)
class ReplenishmentLine:
    id: ReplenishmentLineId
    machine_position_id: SlotId
    product_id: ProductId
    quantity: SignedQuantity
    unit_price: Decimal
    occurred_at: datetime
    product_description_snapshot: str
    preferred_product_id_snapshot: ProductId | None = None
    replacement_reason: ReplacementReason | None = None
    barcode_scanned: Barcode | None = None
    manual_description: str | None = None

    def __post_init__(self) -> None:
        require_aware(self.occurred_at, field_name="occurred_at")
        snapshot = self.product_description_snapshot.strip()
        if not snapshot:
            raise InvalidReplenishmentLineError(
                "product_description_snapshot is required"
            )
        object.__setattr__(self, "product_description_snapshot", snapshot)
        price = Decimal(self.unit_price)
        if price < 0:
            raise InvalidReplenishmentLineError("unit_price must be >= 0")
        object.__setattr__(self, "unit_price", price)
        manual = self.manual_description.strip() if self.manual_description else None
        if manual == "":
            manual = None
        object.__setattr__(self, "manual_description", manual)


@dataclass(slots=True)
class Replenishment:
    """Aggregate root for a replenishment visit."""

    id: ReplenishmentId
    tenant_id: TenantId
    operator_id: UserId
    machine_id: MachineId
    machine_type: MachineType
    started_at: datetime
    location: GeoLocation
    idempotency_key: str
    status: ReplenishmentStatus = ReplenishmentStatus.IN_PROGRESS
    completed_at: datetime | None = None
    version: int = 1
    _lines: list[ReplenishmentLine] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        require_aware(self.started_at, field_name="started_at")
        if not isinstance(self.tenant_id, TenantId):
            raise InvalidReplenishmentStateError("tenant_id is required")
        key = self.idempotency_key.strip()
        if not key:
            raise InvalidReplenishmentStateError("idempotency_key is required")
        self.idempotency_key = key
        if self.version < 1:
            raise InvalidReplenishmentStateError("version must be >= 1")

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
            tenant_id=machine.tenant_id,
            operator_id=operator_id,
            machine_id=machine.id,
            machine_type=machine.type,
            started_at=started_at,
            location=location,
            idempotency_key=idempotency_key,
            status=ReplenishmentStatus.IN_PROGRESS,
            version=1,
        )

    def _ensure_in_progress(self) -> None:
        if self.status != ReplenishmentStatus.IN_PROGRESS:
            raise InvalidReplenishmentStateError(
                f"cannot modify replenishment in status {self.status}"
            )

    def add_line(
        self,
        *,
        machine: Machine,
        slot: MachineSlot,
        product_id: ProductId,
        quantity: SignedQuantity | int,
        unit_price: Decimal | int | float | str,
        occurred_at: datetime,
        product_description_snapshot: str,
        replacement_reason: ReplacementReason | None = None,
        barcode_scanned: Barcode | None = None,
        manual_description: str | None = None,
        line_id: ReplenishmentLineId | None = None,
    ) -> ReplenishmentLine:
        self._ensure_in_progress()
        if machine.id != self.machine_id:
            raise InvalidReplenishmentLineError("line machine mismatch")
        if machine.find_slot(slot.id) is None:
            raise InvalidReplenishmentLineError("slot does not belong to machine")

        signed = (
            quantity if isinstance(quantity, SignedQuantity) else SignedQuantity(quantity)
        )
        validate_operation_capacity(quantity=signed, capacity=slot.capacity)

        price = Decimal(str(unit_price))
        preferred_snapshot, reason = resolve_substitution(
            preferred_product_id=slot.preferred_product_id,
            actual_product_id=product_id,
            configured_price=slot.selling_price,
            unit_price=price,
            replacement_reason=replacement_reason,
        )

        line = ReplenishmentLine(
            id=line_id or ReplenishmentLineId.new(),
            machine_position_id=slot.id,
            product_id=product_id,
            quantity=signed,
            unit_price=price,
            occurred_at=occurred_at,
            product_description_snapshot=product_description_snapshot,
            preferred_product_id_snapshot=preferred_snapshot,
            replacement_reason=reason,
            barcode_scanned=barcode_scanned,
            manual_description=manual_description,
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
