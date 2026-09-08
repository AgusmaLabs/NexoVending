from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.identity.authentication import AuthenticatedIdentity, Principal
from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.identity.errors import IdentityError
from nexo_vending.domain.identity.repositories import OperatorRepository
from nexo_vending.domain.identity.value_objects import Email


@dataclass(frozen=True, slots=True)
class ProvisionOperatorCommand:
    """Provision from authenticated Platform identity + request context.

    Tenant and principal authority come from RequestContext / AuthenticatedIdentity,
    never from client-supplied tenant_id / operator_id fields.
    """

    context: RequestContext
    identity: AuthenticatedIdentity
    role: OperatorRole = OperatorRole.OPERATOR


class ProvisionOperator:
    def __init__(self, operators: OperatorRepository) -> None:
        self._operators = operators

    async def execute(self, command: ProvisionOperatorCommand) -> Operator:
        tenant_id = TenantId.from_raw(command.context.tenant_id)
        principal = (
            command.context.principal
            or Principal.from_authenticated_identity(command.identity)
        )
        if command.context.principal is not None:
            expected = Principal.from_authenticated_identity(command.identity)
            if (
                principal.provider != expected.provider
                or principal.subject != expected.subject
            ):
                raise IdentityError("context principal does not match authenticated identity")

        existing = await self._operators.find_by_principal(tenant_id, principal)
        if existing is not None:
            return existing

        email = Email(command.identity.email) if command.identity.email else None
        operator = Operator.provision(
            operator_id=OperatorId.new(),
            tenant_id=tenant_id,
            principal=principal,
            email=email,
            display_name=command.identity.display_name,
            role=command.role,
        )
        await self._operators.save(operator)
        return operator
