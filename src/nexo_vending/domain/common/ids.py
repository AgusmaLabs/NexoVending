from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class MachineId:
    value: UUID

    @classmethod
    def new(cls) -> MachineId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class ProductId:
    value: UUID

    @classmethod
    def new(cls) -> ProductId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class OperatorId:
    """Stable Vending operator identity."""

    value: UUID

    @classmethod
    def new(cls) -> OperatorId:
        return cls(uuid4())


# Inventory / replenishment continue to reference operators via UserId.
UserId = OperatorId


@dataclass(frozen=True, slots=True)
class TenantId:
    """Tenant isolation key obtained from Platform RequestContext."""

    value: str

    def __post_init__(self) -> None:
        normalized = str(self.value).strip()
        if not normalized:
            raise ValueError("tenant_id is required")
        object.__setattr__(self, "value", normalized)

    @classmethod
    def from_raw(cls, raw: str | UUID) -> TenantId:
        return cls(str(raw))


@dataclass(frozen=True, slots=True)
class ReplenishmentId:
    value: UUID

    @classmethod
    def new(cls) -> ReplenishmentId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class SlotId:
    value: UUID

    @classmethod
    def new(cls) -> SlotId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class InventoryMovementId:
    value: UUID

    @classmethod
    def new(cls) -> InventoryMovementId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class ReplenishmentLineId:
    value: UUID

    @classmethod
    def new(cls) -> ReplenishmentLineId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class InventoryCountId:
    value: UUID

    @classmethod
    def new(cls) -> InventoryCountId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class MachineInventoryPeriodId:
    value: UUID

    @classmethod
    def new(cls) -> MachineInventoryPeriodId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class SnackSaleId:
    value: UUID

    @classmethod
    def new(cls) -> SnackSaleId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class CoffeeSaleId:
    value: UUID

    @classmethod
    def new(cls) -> CoffeeSaleId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class SelectionId:
    value: UUID

    @classmethod
    def new(cls) -> SelectionId:
        return cls(uuid4())
