"""Machine identification without coupling to QR libraries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from nexo_vending.domain.common.ids import MachineId
from nexo_vending.domain.machines.errors import MachineError
from nexo_vending.domain.machines.value_objects import MachineCode


class MachineIdentifierType(StrEnum):
    INTERNAL_ID = "INTERNAL_ID"
    QR_CODE = "QR_CODE"


@dataclass(frozen=True, slots=True)
class MachineIdentifier:
    """Transport-agnostic machine identity (QR is only a capture mechanism)."""

    identifier_type: MachineIdentifierType
    identifier_value: str

    def __post_init__(self) -> None:
        if not isinstance(self.identifier_type, MachineIdentifierType):
            raise MachineError("unknown machine identifier type")
        value = self.identifier_value.strip()
        if not value:
            raise MachineError("machine identifier value is required")
        object.__setattr__(self, "identifier_value", value)

    @classmethod
    def from_raw(cls, identifier_type: str, value: str) -> MachineIdentifier:
        try:
            typed = MachineIdentifierType(str(identifier_type).strip().upper())
        except ValueError as exc:
            raise MachineError(f"unknown machine identifier type: {identifier_type}") from exc
        return cls(identifier_type=typed, identifier_value=value)

    def as_machine_id(self) -> MachineId:
        if self.identifier_type != MachineIdentifierType.INTERNAL_ID:
            raise MachineError("identifier is not an internal machine id")
        try:
            return MachineId(UUID(self.identifier_value))
        except ValueError as exc:
            raise MachineError("invalid machine id") from exc

    def as_machine_code(self) -> MachineCode:
        if self.identifier_type != MachineIdentifierType.QR_CODE:
            raise MachineError("identifier is not a QR / machine code")
        return MachineCode(self.identifier_value)
