from __future__ import annotations

from typing import Protocol

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator


class OperatorRepository(Protocol):
    async def get(self, operator_id: OperatorId) -> Operator | None: ...

    async def save(self, operator: Operator) -> None: ...

    async def find_by_principal(
        self,
        tenant_id: TenantId,
        principal: Principal,
    ) -> Operator | None: ...
