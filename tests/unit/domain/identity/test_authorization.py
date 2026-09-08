from datetime import UTC, datetime, timedelta

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.policies import can_operator_replenish
from nexo_vending.domain.identity.value_objects import ValidityPeriod


def _operator(
    *,
    status: OperatorStatus = OperatorStatus.ACTIVE,
    role: OperatorRole = OperatorRole.OPERATOR,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
) -> Operator:
    start = valid_from or datetime(2026, 1, 1, tzinfo=UTC)
    return Operator(
        id=OperatorId.new(),
        tenant_id=TenantId("tenant-a"),
        principal=Principal(provider="google", subject="123"),
        role=role,
        status=status,
        validity_period=ValidityPeriod(valid_from=start, valid_until=valid_until),
    )


def test_active_operator_can_replenish() -> None:
    at = datetime(2026, 6, 1, tzinfo=UTC)
    assert can_operator_replenish(_operator(), at)


def test_pending_operator_cannot_replenish() -> None:
    at = datetime(2026, 6, 1, tzinfo=UTC)
    assert not can_operator_replenish(_operator(status=OperatorStatus.PENDING), at)


def test_suspended_operator_cannot_replenish() -> None:
    at = datetime(2026, 6, 1, tzinfo=UTC)
    assert not can_operator_replenish(_operator(status=OperatorStatus.SUSPENDED), at)


def test_disabled_operator_cannot_replenish() -> None:
    at = datetime(2026, 6, 1, tzinfo=UTC)
    assert not can_operator_replenish(_operator(status=OperatorStatus.DISABLED), at)


def test_operator_before_validity_cannot_replenish() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    assert not can_operator_replenish(
        _operator(valid_from=start),
        start - timedelta(seconds=1),
    )


def test_operator_after_validity_cannot_replenish() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    assert not can_operator_replenish(
        _operator(valid_from=start, valid_until=end),
        end + timedelta(seconds=1),
    )


def test_operator_at_validity_start_can_replenish() -> None:
    start = datetime(2026, 6, 1, tzinfo=UTC)
    assert can_operator_replenish(_operator(valid_from=start), start)


def test_operator_at_validity_end_cannot_replenish() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    assert not can_operator_replenish(
        _operator(valid_from=start, valid_until=end),
        end,
    )
