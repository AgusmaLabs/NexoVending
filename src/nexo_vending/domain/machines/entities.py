from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from nexo_vending.domain.common.errors import (
    InactiveMachineError,
    InvalidMachineError,
    InvalidSlotError,
)
from nexo_vending.domain.common.ids import MachineId, ProductId, SlotId, TenantId
from nexo_vending.domain.common.value_objects import require_aware
from nexo_vending.domain.machines.enums import MachineStatus, MachineType, SlotStatus
from nexo_vending.domain.machines.errors import (
    InvalidMachineTransitionError,
    InvalidSlotConfigurationError,
    MachineError,
)
from nexo_vending.domain.machines.value_objects import (
    MachineCode,
    MachineLocation,
    SellingPrice,
)

_ALLOWED_TRANSITIONS: dict[MachineStatus, frozenset[MachineStatus]] = {
    MachineStatus.INACTIVE: frozenset({MachineStatus.ACTIVE}),
    MachineStatus.ACTIVE: frozenset({MachineStatus.INACTIVE, MachineStatus.MAINTENANCE}),
    MachineStatus.MAINTENANCE: frozenset({MachineStatus.ACTIVE, MachineStatus.INACTIVE}),
}


@dataclass(slots=True)
class MachineSlot:
    """Physical container/position inside a Machine."""

    id: SlotId
    slot_number: int
    capacity: int
    status: SlotStatus = SlotStatus.ACTIVE
    preferred_product_id: ProductId | None = None
    selling_price: SellingPrice | None = None

    def __post_init__(self) -> None:
        if self.slot_number <= 0:
            raise InvalidSlotError("slot_number must be > 0")
        if self.capacity <= 0:
            raise InvalidSlotError("capacity must be > 0")
        if not isinstance(self.status, SlotStatus):
            raise InvalidSlotConfigurationError("slot status is required")

    @property
    def active(self) -> bool:
        return self.status == SlotStatus.ACTIVE


@dataclass(slots=True)
class Machine:
    """Tenant-scoped machine aggregate root owning physical slots."""

    id: MachineId
    tenant_id: TenantId
    code: MachineCode
    name: str
    type: MachineType
    status: MachineStatus
    created_at: datetime
    updated_at: datetime
    location: MachineLocation | None = None
    sii_id: str | None = None
    _slots: list[MachineSlot] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            raise MachineError("machine requires tenant_id")
        if isinstance(self.code, str):
            self.code = MachineCode(self.code)
        elif not isinstance(self.code, MachineCode):
            raise InvalidMachineError("machine code is required")
        name = self.name.strip()
        if not name:
            raise InvalidMachineError("machine name is required")
        if not isinstance(self.type, MachineType):
            raise InvalidMachineError("machine type is required")
        if not isinstance(self.status, MachineStatus):
            raise InvalidMachineError("machine status is required")
        require_aware(self.created_at, field_name="created_at")
        require_aware(self.updated_at, field_name="updated_at")
        self.name = name
        if self.sii_id is not None:
            sii = self.sii_id.strip()
            self.sii_id = sii or None

    @classmethod
    def create(
        cls,
        *,
        machine_id: MachineId,
        tenant_id: TenantId,
        code: str | MachineCode,
        name: str,
        machine_type: MachineType,
        location: MachineLocation | None = None,
        sii_id: str | None = None,
        created_at: datetime | None = None,
    ) -> Machine:
        now = created_at or datetime.now(UTC)
        return cls(
            id=machine_id,
            tenant_id=tenant_id,
            code=code if isinstance(code, MachineCode) else MachineCode(code),
            name=name,
            type=machine_type,
            status=MachineStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            location=location,
            sii_id=sii_id,
        )

    @property
    def slots(self) -> tuple[MachineSlot, ...]:
        return tuple(self._slots)

    @property
    def active(self) -> bool:
        return self.status == MachineStatus.ACTIVE

    def ensure_can_start_replenishment(self) -> None:
        if self.status != MachineStatus.ACTIVE:
            raise InactiveMachineError(
                f"machine in status {self.status} cannot start replenishment"
            )

    def _touch(self, updated_at: datetime | None = None) -> None:
        self.updated_at = updated_at or datetime.now(UTC)
        require_aware(self.updated_at, field_name="updated_at")

    def _transition_to(self, new_status: MachineStatus) -> None:
        if self.status == new_status:
            return
        allowed = _ALLOWED_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise InvalidMachineTransitionError(
                f"cannot transition machine from {self.status} to {new_status}"
            )
        self.status = new_status
        self._touch()

    def activate(self) -> None:
        self._transition_to(MachineStatus.ACTIVE)

    def deactivate(self) -> None:
        self._transition_to(MachineStatus.INACTIVE)

    def put_in_maintenance(self) -> None:
        self._transition_to(MachineStatus.MAINTENANCE)

    def update_details(
        self,
        *,
        name: str,
        location: MachineLocation | None,
        sii_id: str | None,
    ) -> None:
        cleaned = name.strip()
        if not cleaned:
            raise InvalidMachineError("machine name is required")
        self.name = cleaned
        self.location = location
        self.sii_id = sii_id.strip() if sii_id else None
        self._touch()

    def find_slot(self, slot_id: SlotId) -> MachineSlot | None:
        for slot in self._slots:
            if slot.id == slot_id:
                return slot
        return None

    def find_slot_by_number(self, slot_number: int) -> MachineSlot | None:
        for slot in self._slots:
            if slot.slot_number == slot_number:
                return slot
        return None

    def has_slot(self, slot_number: int) -> bool:
        slot = self.find_slot_by_number(slot_number)
        return slot is not None and slot.active

    def add_slot(
        self,
        *,
        slot_id: SlotId | None = None,
        slot_number: int,
        capacity: int,
        preferred_product_id: ProductId | None = None,
        selling_price: SellingPrice | None = None,
    ) -> MachineSlot:
        # MachineType does NOT restrict whether slots may exist.
        if self.find_slot_by_number(slot_number) is not None:
            raise InvalidSlotConfigurationError(
                f"slot {slot_number} already exists on machine"
            )
        slot = MachineSlot(
            id=slot_id or SlotId.new(),
            slot_number=slot_number,
            capacity=capacity,
            preferred_product_id=preferred_product_id,
            selling_price=selling_price,
            status=SlotStatus.ACTIVE,
        )
        self._slots.append(slot)
        self._touch()
        return slot

    def _require_slot(self, slot_id: SlotId) -> MachineSlot:
        slot = self.find_slot(slot_id)
        if slot is None:
            raise InvalidSlotConfigurationError("slot not found on machine")
        return slot

    def activate_slot(self, slot_id: SlotId) -> MachineSlot:
        slot = self._require_slot(slot_id)
        slot.status = SlotStatus.ACTIVE
        self._touch()
        return slot

    def deactivate_slot(self, slot_id: SlotId) -> MachineSlot:
        slot = self._require_slot(slot_id)
        slot.status = SlotStatus.INACTIVE
        self._touch()
        return slot

    def change_slot_capacity(self, slot_id: SlotId, capacity: int) -> MachineSlot:
        slot = self._require_slot(slot_id)
        if capacity <= 0:
            raise InvalidSlotError("capacity must be > 0")
        slot.capacity = capacity
        self._touch()
        return slot

    def set_preferred_product(
        self,
        slot_id: SlotId,
        product_id: ProductId,
    ) -> MachineSlot:
        slot = self._require_slot(slot_id)
        slot.preferred_product_id = product_id
        self._touch()
        return slot

    def clear_preferred_product(self, slot_id: SlotId) -> MachineSlot:
        slot = self._require_slot(slot_id)
        slot.preferred_product_id = None
        self._touch()
        return slot

    def set_slot_selling_price(
        self,
        slot_id: SlotId,
        price: SellingPrice | Decimal | int | float,
        *,
        currency: str = "CLP",
    ) -> MachineSlot:
        slot = self._require_slot(slot_id)
        if isinstance(price, SellingPrice):
            slot.selling_price = price
        else:
            slot.selling_price = SellingPrice(amount=Decimal(str(price)), currency=currency)
        self._touch()
        return slot
