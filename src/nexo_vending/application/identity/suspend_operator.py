from __future__ import annotations

from dataclasses import dataclass

from nexo_vending.domain.common.ids import OperatorId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorNotFoundError
from nexo_vending.domain.identity.repositories import OperatorRepository


@dataclass(frozen=True, slots=True)
class SuspendOperatorCommand:
    operator_id: OperatorId


class SuspendOperator:
    def __init__(self, operators: OperatorRepository) -> None:
        self._operators = operators

    async def execute(self, command: SuspendOperatorCommand) -> Operator:
        operator = await self._operators.get(command.operator_id)
        if operator is None:
            raise OperatorNotFoundError("operator not found")
        operator.suspend()
        await self._operators.save(operator)
        return operator
