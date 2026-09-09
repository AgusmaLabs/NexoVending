from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import MachineId, TenantId
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.value_objects import MachineCode


class MachineRepository(Protocol):
    async def get(self, machine_id: MachineId) -> Machine | None: ...

    async def find_by_code(
        self,
        tenant_id: TenantId,
        code: MachineCode | str,
    ) -> Machine | None: ...

    async def save(self, machine: Machine) -> None: ...

    async def list_by_tenant(self, tenant_id: TenantId) -> list[Machine]: ...
