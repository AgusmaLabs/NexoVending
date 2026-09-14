"""Issue a Platform session JWT after IdP authentication + Operator acceptance."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.identity import (
    AuthenticationCredentials,
    AuthenticationProvider,
    AuthenticationResult,
    JwtService,
    SessionToken,
)
from nexo_platform.tenant import RequestContext

from nexo_vending.application.identity.resolve_operator import (
    ResolveOperator,
    ResolveOperatorQuery,
)
from nexo_vending.domain.identity.repositories import OperatorRepository


@dataclass(frozen=True, slots=True)
class IssueOperatorSessionCommand:
    id_token: str
    tenant_id: str
    expires_in: int = 3600


class IssueOperatorSession:
    """Authenticate via Platform provider, accept tenant if Operator exists, issue session."""

    def __init__(
        self,
        *,
        authentication: AuthenticationProvider,
        jwt_service: JwtService,
        operators: OperatorRepository,
    ) -> None:
        self._authentication = authentication
        self._jwt = jwt_service
        self._resolve = ResolveOperator(operators)

    async def execute(self, command: IssueOperatorSessionCommand) -> SessionToken:
        credentials = AuthenticationCredentials(
            kind="id_token",
            attributes={"id_token": command.id_token},
        )
        result: AuthenticationResult = await self._authentication.authenticate(credentials)

        tenant_id = str(command.tenant_id).strip()
        context = RequestContext.from_principal(
            principal=result.principal,
            tenant_id=tenant_id,
            operation="auth.session",
        )
        await self._resolve.execute(ResolveOperatorQuery(context=context))

        return self._jwt.issue_session(
            result,
            tenant_id=tenant_id,
            expires_in=command.expires_in,
        )
