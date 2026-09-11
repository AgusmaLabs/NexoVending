"""Ports for machine ↔ replenisher assignments."""

from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import MachineId, OperatorId, TenantId
from nexo_vending.domain.machines.assignment import MachineAssignment


class MachineAssignmentRepository(Protocol):
    async def find_active(
        self,
        *,
        tenant_id: TenantId,
        replenisher_id: OperatorId,
        machine_id: MachineId,
    ) -> MachineAssignment | None: ...

    async def save(self, assignment: MachineAssignment) -> None: ...
