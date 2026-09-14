"""Bootstrap: resolve the authenticated Vending Operator from RequestContext."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.tenant import RequestContext

from nexo_vending.application.identity.resolve_operator import (
    ResolveOperator,
    ResolveOperatorQuery,
)
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.repositories import OperatorRepository


@dataclass(frozen=True, slots=True)
class GetCurrentOperatorQuery:
    context: RequestContext


class GetCurrentOperator:
    def __init__(self, operators: OperatorRepository) -> None:
        self._resolve = ResolveOperator(operators)

    async def execute(self, query: GetCurrentOperatorQuery) -> Operator:
        return await self._resolve.execute(ResolveOperatorQuery(context=query.context))
