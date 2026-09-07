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
class UserId:
    """Operator / user identity reference used by Vending."""

    value: UUID

    @classmethod
    def new(cls) -> UserId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class ReplenishmentId:
    value: UUID

    @classmethod
    def new(cls) -> ReplenishmentId:
        return cls(uuid4())


@dataclass(frozen=True, slots=True)
class InventoryMovementId:
    value: UUID

    @classmethod
    def new(cls) -> InventoryMovementId:
        return cls(uuid4())
