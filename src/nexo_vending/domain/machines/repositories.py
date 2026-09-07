from __future__ import annotations

from typing import Protocol

from nexo_vending.domain.common.ids import MachineId
from nexo_vending.domain.machines.entities import Machine


class MachineRepository(Protocol):
    async def get(self, machine_id: MachineId) -> Machine | None: ...

    async def get_by_code(self, code: str) -> Machine | None: ...

    async def save(self, machine: Machine) -> None: ...
