from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, TenantId
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.errors import CrossTenantMachineAccessError, MachineError
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.machines.value_objects import MachineCode


@dataclass(frozen=True, slots=True)
class GetMachineQuery:
    context: RequestContext
    machine_id: MachineId


class GetMachine:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, query: GetMachineQuery) -> Machine:
        tenant_id = TenantId.from_raw(query.context.tenant_id)
        machine = await self._machines.get(query.machine_id)
        if machine is None:
            raise MachineError("machine not found")
        if machine.tenant_id != tenant_id:
            raise CrossTenantMachineAccessError("cannot read machine from another tenant")
        return machine


@dataclass(frozen=True, slots=True)
class FindMachineByCodeQuery:
    context: RequestContext
    code: str


class FindMachineByCode:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, query: FindMachineByCodeQuery) -> Machine | None:
        tenant_id = TenantId.from_raw(query.context.tenant_id)
        return await self._machines.find_by_code(tenant_id, MachineCode(query.code))


@dataclass(frozen=True, slots=True)
class ListMachineSlotsQuery:
    context: RequestContext
    machine_id: MachineId


class ListMachineSlots:
    def __init__(self, machines: MachineRepository) -> None:
        self._machines = machines

    async def execute(self, query: ListMachineSlotsQuery) -> tuple[MachineSlot, ...]:
        machine = await GetMachine(self._machines).execute(
            GetMachineQuery(context=query.context, machine_id=query.machine_id)
        )
        return machine.slots
