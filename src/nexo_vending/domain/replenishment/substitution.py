from __future__ import annotations

from decimal import Decimal

from nexo_vending.domain.common.errors import SubstitutionRejectedError
from nexo_vending.domain.common.ids import ProductId
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.replenishment.enums import ReplacementReason


def resolve_substitution(
    *,
    preferred_product_id: ProductId | None,
    actual_product_id: ProductId,
    configured_price: SellingPrice | None,
    unit_price: Decimal,
    replacement_reason: ReplacementReason | None,
) -> tuple[ProductId | None, ReplacementReason | None]:
    """Validate substitution; preferred product is never mutated by this helper."""
    if preferred_product_id is None or preferred_product_id == actual_product_id:
        return preferred_product_id, None

    if replacement_reason is None:
        raise SubstitutionRejectedError("substitution requires replacement_reason")
    if configured_price is None:
        raise SubstitutionRejectedError(
            "substitution requires configured slot selling price"
        )
    if Decimal(unit_price) != configured_price.amount:
        raise SubstitutionRejectedError(
            "substitution requires unit_price to match configured selling price"
        )
    return preferred_product_id, replacement_reason
