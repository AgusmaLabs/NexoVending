from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.errors import (
    IdentityError,
    InvalidOperatorTransitionError,
)
from nexo_vending.domain.identity.value_objects import Email, ValidityPeriod


@dataclass(slots=True)
class Operator:
    """Tenant-scoped Vending operator bound to a Platform Principal."""

    id: OperatorId
    tenant_id: TenantId
    principal: Principal
    role: OperatorRole
    status: OperatorStatus
    validity_period: ValidityPeriod
    email: Email | None = None
    display_name: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.tenant_id, TenantId):
            raise IdentityError("operator requires tenant_id")
        if not isinstance(self.principal, Principal):
            raise IdentityError("operator requires platform Principal")
        if self.display_name is not None:
            name = self.display_name.strip()
            self.display_name = name or None

    @classmethod
    def provision(
        cls,
        *,
        operator_id: OperatorId,
        tenant_id: TenantId,
        principal: Principal,
        email: Email | None = None,
        display_name: str | None = None,
        role: OperatorRole = OperatorRole.OPERATOR,
        valid_from: datetime | None = None,
    ) -> Operator:
        started = valid_from or datetime.now(UTC)
        return cls(
            id=operator_id,
            tenant_id=tenant_id,
            principal=principal,
            email=email,
            display_name=display_name,
            role=role,
            status=OperatorStatus.PENDING,
            validity_period=ValidityPeriod(valid_from=started, valid_until=None),
        )

    def activate(self) -> None:
        if self.status == OperatorStatus.DISABLED:
            raise InvalidOperatorTransitionError("disabled operator cannot be activated")
        if self.status not in {OperatorStatus.PENDING, OperatorStatus.SUSPENDED}:
            if self.status == OperatorStatus.ACTIVE:
                return
            raise InvalidOperatorTransitionError(
                f"cannot activate operator from status {self.status}"
            )
        self.status = OperatorStatus.ACTIVE

    def suspend(self) -> None:
        if self.status == OperatorStatus.DISABLED:
            raise InvalidOperatorTransitionError("disabled operator cannot be suspended")
        if self.status != OperatorStatus.ACTIVE:
            raise InvalidOperatorTransitionError(
                f"cannot suspend operator from status {self.status}"
            )
        self.status = OperatorStatus.SUSPENDED

    def disable(self) -> None:
        if self.status == OperatorStatus.DISABLED:
            return
        if self.status not in {OperatorStatus.ACTIVE, OperatorStatus.SUSPENDED}:
            raise InvalidOperatorTransitionError(
                f"cannot disable operator from status {self.status}"
            )
        self.status = OperatorStatus.DISABLED

    def assign_role(self, role: OperatorRole) -> None:
        if self.status == OperatorStatus.DISABLED:
            raise InvalidOperatorTransitionError("disabled operator cannot change role")
        self.role = role
