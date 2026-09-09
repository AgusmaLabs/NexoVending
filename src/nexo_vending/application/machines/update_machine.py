from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_machines
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.errors import CrossTenantMachineAccessError, MachineError
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.machines.value_objects import MachineLocation


@dataclass(frozen=True, slots=True)
class UpdateMachineCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId
    name: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    sii_id: str | None = None


class UpdateMachine:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, command: UpdateMachineCommand) -> Machine:
        if not can_manage_machines(command.acting_operator):
            raise OperatorAuthorizationError("operator cannot manage machines")

        tenant_id = TenantId.from_raw(command.context.tenant_id)
        if command.acting_operator.tenant_id != tenant_id:
            raise OperatorAuthorizationError("operator tenant mismatch")

        machine = await self._machines.get(command.machine_id)
        if machine is None:
            raise MachineError("machine not found")
        if machine.tenant_id != tenant_id:
            raise CrossTenantMachineAccessError("cannot update machine from another tenant")

        location = None
        if command.address is not None:
            if command.latitude is None or command.longitude is None:
                raise MachineError("location requires address, latitude and longitude")
            location = MachineLocation(
                address=command.address,
                latitude=command.latitude,
                longitude=command.longitude,
            )

        machine.update_details(name=command.name, location=location, sii_id=command.sii_id)
        await self._machines.save(machine)
        return machine
