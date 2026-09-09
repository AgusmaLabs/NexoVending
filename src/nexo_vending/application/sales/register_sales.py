from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from nexo_vending.domain.common.ids import (
    CoffeeSaleId,
    MachineId,
    ProductId,
    SelectionId,
    SlotId,
    SnackSaleId,
)
from nexo_vending.domain.sales.entities import (
    CoffeeSale,
    Recipe,
    SnackSale,
    register_coffee_sale,
    register_snack_sale,
)


@dataclass(frozen=True, slots=True)
class RegisterSnackSaleCommand:
    machine_id: MachineId
    slot_id: SlotId
    quantity: int
    occurred_at: datetime
    product_id: ProductId | None = None


class RegisterSnackSale:
    async def execute(self, command: RegisterSnackSaleCommand) -> SnackSale:
        return register_snack_sale(
            sale_id=SnackSaleId.new(),
            machine_id=command.machine_id,
            slot_id=command.slot_id,
            quantity=command.quantity,
            occurred_at=command.occurred_at,
            product_id=command.product_id,
        )


@dataclass(frozen=True, slots=True)
class RegisterCoffeeSaleCommand:
    machine_id: MachineId
    recipe: Recipe | None
    quantity: int
    occurred_at: datetime
    available_stock: dict[ProductId, int] | None = None
    container_by_product: dict[ProductId, SlotId] | None = None
    selection_id: SelectionId | None = None


class RegisterCoffeeSale:
    async def execute(self, command: RegisterCoffeeSaleCommand) -> CoffeeSale:
        return register_coffee_sale(
            sale_id=CoffeeSaleId.new(),
            machine_id=command.machine_id,
            recipe=command.recipe,
            quantity=command.quantity,
            occurred_at=command.occurred_at,
            available_stock=command.available_stock,
            container_by_product=command.container_by_product,
        )
