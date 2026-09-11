from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from nexo_vending.domain.common.errors import DomainError, InsufficientStockError
from nexo_vending.domain.common.ids import ProductId, ReplenishmentId, SlotId, TenantId
from nexo_vending.domain.common.value_objects import Barcode, SignedQuantity
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.inventory.repositories import InventoryRepository
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.products.repositories import ProductRepository
from nexo_vending.domain.products.services import ProductLookup
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.domain.replenishment.enums import ReplacementReason
from nexo_vending.domain.replenishment.repositories import ReplenishmentRepository


@dataclass(frozen=True, slots=True)
class AddReplenishmentLineCommand:
    replenishment_id: ReplenishmentId
    tenant_id: TenantId
    slot_id: SlotId
    quantity: int
    scanned_at: datetime
    unit_price: Decimal | int | float | str | None = None
    barcode: str | None = None
    manual_description: str | None = None
    product_id: ProductId | None = None
    replacement_reason: ReplacementReason | None = None


class AddReplenishmentLine:
    def __init__(
        self,
        replenishments: ReplenishmentRepository,
        machines: MachineRepository,
        product_lookup: ProductLookup,
        inventory: InventoryRepository,
        products: ProductRepository | None = None,
    ) -> None:
        self._replenishments = replenishments
        self._machines = machines
        self._product_lookup = product_lookup
        self._inventory = inventory
        self._products = products

    async def execute(self, command: AddReplenishmentLineCommand) -> Replenishment:
        replenishment = await self._replenishments.get(command.replenishment_id)
        if replenishment is None:
            raise DomainError("replenishment not found")
        if replenishment.tenant_id != command.tenant_id:
            raise DomainError("replenishment not found")

        machine = await self._machines.get(replenishment.machine_id)
        if machine is None:
            raise DomainError("machine not found")
        slot = machine.find_slot(command.slot_id)
        if slot is None:
            raise DomainError("slot not found on machine")

        barcode = Barcode(command.barcode) if command.barcode is not None else None
        product_id = command.product_id
        snapshot = ""
        manual = command.manual_description

        if product_id is None and barcode is not None:
            product = await self._product_lookup.find_by_barcode(
                command.tenant_id,
                barcode,
            )
            if product is not None:
                product_id = product.id
                snapshot = product.display_name
            elif manual and manual.strip():
                snapshot = manual.strip()
            else:
                raise DomainError("product not found")
        elif product_id is not None:
            if self._products is not None:
                product = await self._products.get(product_id)
                if product is None or product.tenant_id != command.tenant_id:
                    raise DomainError("product not found")
                snapshot = (manual or "").strip() or product.display_name
            else:
                snapshot = (manual or "").strip() or "product"
        elif manual and manual.strip():
            snapshot = manual.strip()
        else:
            raise DomainError("line requires product identity or manual_description")

        if not snapshot:
            snapshot = "product"

        if command.unit_price is not None:
            unit_price: Decimal | int | float | str = command.unit_price
        elif slot.selling_price is not None:
            unit_price = slot.selling_price.amount
        else:
            raise DomainError("slot has no selling_price; unit_price is required")

        quantity = SignedQuantity(command.quantity)
        if product_id is not None and quantity.is_load:
            available = await self._inventory.expected_quantity(
                InventoryLocation.replenisher(replenishment.operator_id),
                product_id,
            )
            if quantity.absolute > available:
                raise InsufficientStockError(
                    f"insufficient replenisher inventory: need {quantity.absolute}, have {available}"
                )

        replenishment.add_line(
            machine=machine,
            slot=slot,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            occurred_at=command.scanned_at,
            product_description_snapshot=snapshot,
            replacement_reason=command.replacement_reason,
            barcode_scanned=barcode,
            manual_description=manual,
        )
        await self._replenishments.save(replenishment)
        return replenishment
