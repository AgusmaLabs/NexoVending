"""Machine operational access policy."""

from __future__ import annotations

from datetime import datetime

from nexo_vending.domain.common.value_objects import require_aware
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.policies import can_operator_replenish
from nexo_vending.domain.machines.assignment import MachineAssignment
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineStatus
from nexo_vending.domain.machines.errors import MachineAccessDeniedError, MachineError


class MachineAccessPolicy:
    """Decide whether an operator may execute replenishment on a machine."""

    def ensure_can_operate(
        self,
        *,
        operator: Operator,
        machine: Machine,
        assignment: MachineAssignment | None,
        at: datetime,
    ) -> None:
        require_aware(at, field_name="at")
        if operator.tenant_id != machine.tenant_id:
            raise MachineAccessDeniedError("operator cannot access machine from another tenant")
        if machine.status != MachineStatus.ACTIVE:
            raise MachineError("machine is not active")
        if operator.status != OperatorStatus.ACTIVE:
            raise MachineAccessDeniedError("operator is not active")

        if operator.role == OperatorRole.ADMIN:
            # Admins manage inventory/catalog; they do not replenish by default.
            raise MachineAccessDeniedError("admin cannot replenish machines")

        if not can_operator_replenish(operator, at):
            raise MachineAccessDeniedError("operator cannot replenish")

        if assignment is None or not assignment.is_effective_at(at):
            raise MachineAccessDeniedError("replenisher is not assigned to this machine")
        if assignment.tenant_id != machine.tenant_id:
            raise MachineAccessDeniedError("assignment tenant mismatch")
        if assignment.machine_id != machine.id:
            raise MachineAccessDeniedError("assignment machine mismatch")
        if assignment.replenisher_id != operator.id:
            raise MachineAccessDeniedError("assignment replenisher mismatch")
