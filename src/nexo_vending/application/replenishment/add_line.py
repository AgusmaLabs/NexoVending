from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.errors import DomainError
from nexo_vending.domain.common.ids import ProductId, ReplenishmentId
from nexo_vending.domain.common.value_objects import Barcode, Quantity
from nexo_vending.domain.products.services import ProductLookup
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class AddReplenishmentLineCommand:
    replenishment_id: ReplenishmentId
    barcode: str | None
    quantity: int
    slot: int | None
    scanned_at: datetime
    manual_description: str | None = None
    product_id: ProductId | None = None


class AddReplenishmentLine:
    def __init__(
        self,
        replenishments: ReplenishmentRepository,
        product_lookup: ProductLookup,
    ) -> None:
        self._replenishments = replenishments
        self._product_lookup = product_lookup

    async def execute(self, command: AddReplenishmentLineCommand) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None:
            raise DomainError("replenishment not found")

        barcode = Barcode(command.barcode) if command.barcode is not None else None
        product_id = command.product_id
        snapshot = ""
        manual = command.manual_description

        if product_id is None and barcode is not None:
            product = await self._product_lookup.find_by_barcode(barcode)
            if product is not None:
                product_id = product.id
                snapshot = product.name
            elif manual:
                snapshot = manual.strip()
            else:
                raise DomainError("unknown product requires manual_description")
        elif product_id is not None:
            # Caller provided identity; snapshot still required on the line.
            snapshot = (manual or "").strip() or "product"
        elif manual:
            snapshot = manual.strip()
        else:
            raise DomainError("line requires product identity or manual_description")

        if product_id is not None and not snapshot:
            snapshot = "product"

        replenishment.add_line(
            product_id=product_id,
            barcode_scanned=barcode,
            product_description_snapshot=snapshot,
            manual_description=manual if product_id is None else None,
            quantity=Quantity(command.quantity),
            slot=command.slot,
            scanned_at=command.scanned_at,
        )
        await self._replenishments.save(replenishment)
        return replenishment
