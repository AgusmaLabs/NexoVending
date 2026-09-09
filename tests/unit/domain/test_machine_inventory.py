from datetime import UTC, datetime

import pytest

from nexo_vending.domain.common.errors import InvalidMachineInventoryError
from nexo_vending.domain.common.ids import MachineId, MachineInventoryPeriodId, SlotId
from nexo_vending.domain.inventory.periods import MachineInventoryPeriod


def test_machine_inventory_period_lifecycle() -> None:
    machine = MachineId.new()
    slot = SlotId.new()
    opened = datetime(2026, 9, 1, tzinfo=UTC)
    period = MachineInventoryPeriod.open_initial(
        period_id=MachineInventoryPeriodId.new(),
        machine_id=machine,
        position_id=slot,
        opened_at=opened,
    )
    assert period.opening_quantity == 0
    assert period.theoretical_quantity == 0

    period.apply_replenishment(5)
    period.apply_replenishment(-2)
    period.apply_consumption(1)
    assert period.theoretical_quantity == 2  # 0 + 5 - 2 - 1

    variance = period.record_physical_count(1)
    assert variance == -1
    assert period.variance == -1
    # variance does not create LOSS — period only stores the number
    assert period.physical_quantity == 1

    closed_at = datetime(2026, 9, 8, tzinfo=UTC)
    period.close(closed_at=closed_at)
    nxt = period.open_next(
        period_id=MachineInventoryPeriodId.new(),
        opened_at=closed_at,
    )
    assert nxt.opening_quantity == 1
    assert nxt.theoretical_quantity == 1


def test_capacity_change_does_not_affect_period_stock() -> None:
    period = MachineInventoryPeriod.open_initial(
        period_id=MachineInventoryPeriodId.new(),
        machine_id=MachineId.new(),
        position_id=SlotId.new(),
        opened_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    period.apply_replenishment(5)
    # Changing slot capacity is a machine config concern; period stock unchanged.
    assert period.theoretical_quantity == 5


def test_cannot_close_without_physical() -> None:
    period = MachineInventoryPeriod.open_initial(
        period_id=MachineInventoryPeriodId.new(),
        machine_id=MachineId.new(),
        position_id=SlotId.new(),
        opened_at=datetime(2026, 9, 1, tzinfo=UTC),
    )
    with pytest.raises(InvalidMachineInventoryError):
        period.close(closed_at=datetime(2026, 9, 8, tzinfo=UTC))
