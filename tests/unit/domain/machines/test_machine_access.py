"""Domain tests for machine identification and access."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import MachineId, OperatorId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.machines.access import MachineAccessPolicy
from nexo_vending.domain.machines.assignment import MachineAssignment
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.errors import MachineAccessDeniedError, MachineError
from nexo_vending.domain.machines.identifiers import MachineIdentifier, MachineIdentifierType


def test_machine_identifier_rejects_empty_and_unknown() -> None:
    with pytest.raises(MachineError):
        MachineIdentifier.from_raw("QR_CODE", "  ")
    with pytest.raises(MachineError):
        MachineIdentifier.from_raw("CAMERA", "X")


def test_machine_identifier_types() -> None:
    qr = MachineIdentifier.from_raw("QR_CODE", "mix-001")
    assert qr.identifier_type == MachineIdentifierType.QR_CODE
    assert qr.as_machine_code().value == "MIX-001"
    mid = MachineId.new()
    internal = MachineIdentifier.from_raw("INTERNAL_ID", str(mid.value))
    assert internal.as_machine_id() == mid


def test_machine_access_requires_assignment() -> None:
    tenant = TenantId("t1")
    machine = Machine.create(
        machine_id=MachineId.new(),
        tenant_id=tenant,
        code="M1",
        name="A",
        machine_type=MachineType.SNACK,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator = Operator.provision(
        operator_id=OperatorId.new(),
        tenant_id=tenant,
        principal=Principal(provider="google", subject="r1"),
        role=OperatorRole.OPERATOR,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
    )
    operator.activate()
    policy = MachineAccessPolicy()
    now = datetime(2026, 6, 1, tzinfo=UTC)
    with pytest.raises(MachineAccessDeniedError):
        policy.ensure_can_operate(
            operator=operator, machine=machine, assignment=None, at=now
        )

    assignment = MachineAssignment.create(
        tenant_id=tenant,
        replenisher_id=operator.id,
        machine_id=machine.id,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=datetime(2026, 2, 1, tzinfo=UTC),
    )
    with pytest.raises(MachineAccessDeniedError):
        policy.ensure_can_operate(
            operator=operator, machine=machine, assignment=assignment, at=now
        )

    ok = MachineAssignment.create(
        tenant_id=tenant,
        replenisher_id=operator.id,
        machine_id=machine.id,
        valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        valid_until=now + timedelta(days=1),
    )
    policy.ensure_can_operate(
        operator=operator, machine=machine, assignment=ok, at=now
    )
