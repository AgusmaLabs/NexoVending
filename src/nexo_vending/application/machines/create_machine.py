from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_machines
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.errors import DuplicateMachineCodeError
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.machines.value_objects import MachineCode, MachineLocation


@dataclass(frozen=True, slots=True)
class CreateMachineCommand:
    context: RequestContext
    acting_operator: Operator
    code: str
    name: str
    machine_type: MachineType
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    sii_id: str | None = None
    claimed_tenant_id: str | None = None


class CreateMachine:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: CreateMachineCommand) -> Machine:
        if not can_manage_machines(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage machines")

        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.claimed_tenant_id is not None:
            if str(command.claimed_tenant_id).strip() != tenant_id.value:
                raise OperatorAuthorizationError("client cannot override tenant_id")
        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")

        code = MachineCode(command.code)
        existing = await self._machines.find_by_code(tenant_id, code)
        if existing is not None:
            raise DuplicateMachineCodeError("machine code already exists in tenant")

        location = None
        if command.address is not None:
            if command.latitude is None or command.longitude is None:
                from nexo_vending.domain.machines.errors import MachineError

                raise MachineError("location requires address, latitude and longitude")
            location = MachineLocation(
                address=command.address,
                latitude=command.latitude,
                longitude=command.longitude,
            )

        machine = Machine.create(
            machine_id=MachineId.new(),
            tenant_id=tenant_id,
            code=code,
            name=command.name,
            machine_type=command.machine_type,
            location=location,
            sii_id=command.sii_id,
        )
        await self._machines.save(machine)
        return machine
