from __future__ import annotations

from nexo_vending.domain.common.errors import CapacityExceededError
from nexo_vending.domain.common.value_objects import SignedQuantity


def validate_operation_capacity(*, quantity: SignedQuantity, capacity: int) -> None:
    """Capacity limits each operation independently: 0 < abs(qty) <= capacity."""
    if capacity <= 0:
        raise CapacityExceededError("slot capacity must be > 0")
    absolute = quantity.absolute
    if not 0 < absolute <= capacity:
        raise CapacityExceededError(
            f"quantity abs({quantity.value}) exceeds capacity {capacity}"
        )
