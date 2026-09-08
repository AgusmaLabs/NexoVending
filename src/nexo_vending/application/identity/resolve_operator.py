from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import IdentityError, OperatorNotFoundError
from nexo_vending.domain.identity.repositories import OperatorRepository


@dataclass(frozen=True, slots=True)
class ResolveOperatorQuery:
    """Resolve operator using only authenticated RequestContext authority."""

    context: RequestContext
    # Explicitly ignored if provided — documents that clients cannot override.
    claimed_tenant_id: str | None = None
    claimed_operator_id: str | None = None


class ResolveOperator:
    def __init__(self, operators: OperatorRepository) -> None:
        self._operators = operators

    async def execute(self, query: ResolveOperatorQuery) -> Operator:
        if query.claimed_tenant_id is not None:
            claimed = str(query.claimed_tenant_id).strip()
            actual = str(query.context.tenant_id).strip()
            if claimed != actual:
                raise IdentityError("client cannot override tenant_id")

        if query.claimed_operator_id is not None:
            raise IdentityError("client cannot override actor/operator_id")

        if query.context.principal is None:
            raise IdentityError("RequestContext.principal is required")

        tenant_id = TenantId.from_raw(query.context.tenant_id)
        operator = await self._operators.find_by_principal(
            tenant_id,
            query.context.principal,
        )
        if operator is None:
            raise OperatorNotFoundError("operator not found for tenant + principal")
        if operator.tenant_id != tenant_id:
            raise IdentityError("cross-tenant operator access is rejected")
        return operator
