from datetime import UTC, datetime

import pytest
from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.errors import IdentityError, InvalidOperatorTransitionError
from nexo_vending.domain.identity.value_objects import ValidityPeriod


def _operator(**overrides) -> Operator:
    data = {
        "id": OperatorId.new(),
        "tenant_id": TenantId("tenant-a"),
        "principal": Principal(provider="google", subject="123"),
        "role": OperatorRole.OPERATOR,
        "status": OperatorStatus.PENDING,
        "validity_period": ValidityPeriod(
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            valid_until=None,
        ),
    }
    data.update(overrides)
    return Operator(**data)


def test_operator_requires_tenant() -> None:
    with pytest.raises((IdentityError, TypeError, ValueError)):
        Operator(
            id=OperatorId.new(),
            tenant_id=None,  # type: ignore[arg-type]
            principal=Principal(provider="google", subject="1"),
            role=OperatorRole.OPERATOR,
            status=OperatorStatus.PENDING,
            validity_period=ValidityPeriod(valid_from=datetime(2026, 1, 1, tzinfo=UTC)),
        )


def test_operator_requires_principal() -> None:
    with pytest.raises((IdentityError, TypeError)):
        Operator(
            id=OperatorId.new(),
            tenant_id=TenantId("tenant-a"),
            principal=None,  # type: ignore[arg-type]
            role=OperatorRole.OPERATOR,
            status=OperatorStatus.PENDING,
            validity_period=ValidityPeriod(valid_from=datetime(2026, 1, 1, tzinfo=UTC)),
        )


def test_operator_starts_pending() -> None:
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=TenantId("tenant-a"),
        principal=Principal(provider="google", subject="123"),
    )
    assert operator.status == OperatorStatus.PENDING


def test_operator_can_be_activated() -> None:
    operator = _operator()
    operator.activate()
    assert operator.status == OperatorStatus.ACTIVE


def test_operator_can_be_suspended() -> None:
    operator = _operator(status=OperatorStatus.ACTIVE)
    operator.suspend()
    assert operator.status == OperatorStatus.SUSPENDED


def test_operator_can_be_disabled() -> None:
    operator = _operator(status=OperatorStatus.ACTIVE)
    operator.disable()
    assert operator.status == OperatorStatus.DISABLED


def test_pending_can_activate() -> None:
    operator = _operator(status=OperatorStatus.PENDING)
    operator.activate()
    assert operator.status == OperatorStatus.ACTIVE


def test_active_can_suspend() -> None:
    operator = _operator(status=OperatorStatus.ACTIVE)
    operator.suspend()
    assert operator.status == OperatorStatus.SUSPENDED


def test_suspended_can_activate() -> None:
    operator = _operator(status=OperatorStatus.SUSPENDED)
    operator.activate()
    assert operator.status == OperatorStatus.ACTIVE


def test_active_can_disable() -> None:
    operator = _operator(status=OperatorStatus.ACTIVE)
    operator.disable()
    assert operator.status == OperatorStatus.DISABLED


def test_suspended_can_disable() -> None:
    operator = _operator(status=OperatorStatus.SUSPENDED)
    operator.disable()
    assert operator.status == OperatorStatus.DISABLED


def test_disabled_is_terminal() -> None:
    operator = _operator(status=OperatorStatus.DISABLED)
    with pytest.raises(InvalidOperatorTransitionError):
        operator.activate()


def test_disabled_cannot_activate() -> None:
    operator = _operator(status=OperatorStatus.DISABLED)
    with pytest.raises(InvalidOperatorTransitionError):
        operator.activate()


def test_disabled_cannot_suspend() -> None:
    operator = _operator(status=OperatorStatus.DISABLED)
    with pytest.raises(InvalidOperatorTransitionError):
        operator.suspend()
