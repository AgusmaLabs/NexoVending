"""Machine ↔ replenisher assignment (operational access)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from nexo_vending.domain.common.ids import MachineId, OperatorId, TenantId
from nexo_vending.domain.common.value_objects import require_aware
from nexo_vending.domain.identity.value_objects import ValidityPeriod
from nexo_vending.domain.machines.errors import MachineError


class MachineAssignmentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


@dataclass(frozen=True, slots=True)
class MachineAssignmentId:
    value: UUID

    @classmethod
    def new(cls) -> MachineAssignmentId:
        return cls(uuid4())


@dataclass(slots=True)
class MachineAssignment:
    """Authorizes a replenisher to operate a machine within a validity window."""

    id: MachineAssignmentId
    tenant_id: TenantId
    replenisher_id: OperatorId
    machine_id: MachineId
    validity_period: ValidityPeriod
    status: MachineAssignmentStatus = MachineAssignmentStatus.ACTIVE

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            raise MachineError("assignment requires tenant_id")
        if not isinstance(self.validity_period, ValidityPeriod):
            raise MachineError("assignment requires validity_period")

    @classmethod
    def create(
        cls,
        *,
        assignment_id: MachineAssignmentId | None = None,
        tenant_id: TenantId,
        replenisher_id: OperatorId,
        machine_id: MachineId,
        valid_from: datetime,
        valid_until: datetime | None = None,
    ) -> MachineAssignment:
        return cls(
            id=assignment_id or MachineAssignmentId.new(),
            tenant_id=tenant_id,
            replenisher_id=replenisher_id,
            machine_id=machine_id,
            validity_period=ValidityPeriod(valid_from=valid_from, valid_until=valid_until),
            status=MachineAssignmentStatus.ACTIVE,
        )

    def is_effective_at(self, at: datetime) -> bool:
        require_aware(at, field_name="at")
        return (
            self.status == MachineAssignmentStatus.ACTIVE
            and self.validity_period.is_valid_at(at)
        )

    def revoke(self) -> None:
        self.status = MachineAssignmentStatus.REVOKED
