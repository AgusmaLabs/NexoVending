"""Resolve a machine from an identifier for replenishment execution."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.machines.access import MachineAccessPolicy
from nexo_vending.domain.machines.assignment_repository import MachineAssignmentRepository
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.errors import MachineError
from nexo_vending.domain.machines.identifiers import (
    MachineIdentifier,
    MachineIdentifierType,
)
from nexo_vending.domain.machines.repositories import MachineRepository


@dataclass(frozen=True, slots=True)
class ResolveMachineQuery:
    context: RequestContext
    identifier: MachineIdentifier
    acting_operator: Operator
    at: datetime | None = None


class ResolveMachine:
    def __init__(
        self,
        machines: MachineRepository,
        assignments: MachineAssignmentRepository,
        *,
        access_policy: MachineAccessPolicy | None = None,
    ) -> None:
        self._machines = machines
        self._assignments = assignments
        self._access = access_policy or MachineAccessPolicy()

    async def execute(self, query: ResolveMachineQuery) -> Machine:
        tenant_id = TenantId.from_raw(query.context.tenant_id)
        at = query.at or datetime.now(UTC)
        machine = await self._load(tenant_id, query.identifier)
        if machine is None:
            raise MachineError("machine not found")
        if machine.tenant_id != tenant_id:
            raise MachineError("machine not found")

        assignment = await self._assignments.find_active(
            tenant_id=tenant_id,
            replenisher_id=query.acting_operator.id,
            machine_id=machine.id,
        )
        self._access.ensure_can_operate(
            operator=query.acting_operator,
            machine=machine,
            assignment=assignment,
            at=at,
        )
        return machine

    async def _load(
        self,
        tenant_id: TenantId,
        identifier: MachineIdentifier,
    ) -> Machine | None:
        if identifier.identifier_type == MachineIdentifierType.INTERNAL_ID:
            return await self._machines.get(identifier.as_machine_id())
        if identifier.identifier_type == MachineIdentifierType.QR_CODE:
            return await self._machines.find_by_code(tenant_id, identifier.as_machine_code())
        raise MachineError("unsupported machine identifier type")
