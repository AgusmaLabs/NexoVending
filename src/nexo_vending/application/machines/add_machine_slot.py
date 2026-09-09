from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from nexo_platform.tenant import RequestContext

from nexo_vending.domain.common.ids import MachineId, ProductId, TenantId
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.errors import OperatorAuthorizationError
from nexo_vending.domain.identity.policies import can_manage_machines
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.errors import CrossTenantMachineAccessError, MachineError
from nexo_vending.domain.machines.repositories import MachineRepository
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.products.enums import ProductStatus
from nexo_vending.domain.products.repositories import ProductRepository


@dataclass(frozen=True, slots=True)
class AddMachineSlotCommand:
    context: RequestContext
    acting_operator: Operator
    machine_id: MachineId
    slot_number: int
    capacity: int
    preferred_product_id: ProductId | None = None
    selling_price: Decimal | None = None
    currency: str = "CLP"


class AddMachineSlot:
    def __init__(
        self,
        machines: MachineRepository,
        products: ProductRepository | None = None,
    ) -> None:
        self._machines = machines
        self._products = products

    async def execute(self, command: AddMachineSlotCommand) -> MachineSlot:
        machine = await _load_managed_machine(
            self._machines, command.context, command.acting_operator, command.machine_id
        )
        if command.preferred_product_id is not None:
            await _require_active_same_tenant_product(
                self._products,
                product_id=command.preferred_product_id,
                tenant_id=machine.tenant_id,
            )
        price = None
        if command.selling_price is not None:
            price = SellingPrice(amount=command.selling_price, currency=command.currency)
        slot = machine.add_slot(
            slot_number=command.slot_number,
            capacity=command.capacity,
            preferred_product_id=command.preferred_product_id,
            selling_price=price,
        )
        await self._machines.save(machine)
        return slot


async def _require_active_same_tenant_product(
    products: ProductRepository | None,
    *,
    product_id: ProductId,
    tenant_id: TenantId,
) -> None:
    if products is None:
        raise MachineError("product repository required to set preferred product")
    product = await products.get(product_id)
    if product is None:
        raise MachineError("preferred product not found")
    if product.tenant_id != tenant_id:
        raise MachineError("preferred product must belong to the same tenant")
    if product.status != ProductStatus.ACTIVE:
        raise MachineError("preferred product must be active")


async def _load_managed_machine(
    machines: MachineRepository,
    context: RequestContext,
    operator: Operator,
    machine_id: MachineId,
) -> Machine:
    if not can_manage_machines(operator):
        raise OperatorAuthorizationError("operator cannot manage machines")
    tenant_id = TenantId.from_raw(context.tenant_id)
    if operator.tenant_id != tenant_id:
        raise OperatorAuthorizationError("operator tenant mismatch")
    machine = await machines.get(machine_id)
    if machine is None:
        raise MachineError("machine not found")
    if machine.tenant_id != tenant_id:
        raise CrossTenantMachineAccessError("cannot modify machine from another tenant")
    return machine
