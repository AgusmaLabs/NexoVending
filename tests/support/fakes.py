"""In-memory fakes for domain/application tests (not production adapters)."""

from __future__ import annotations

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import (
    MachineId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import Barcode, Quantity
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.replenishment.entities import Replenishment


class InMemoryProductRepository:
    def __init__(self) -> None:
        self._by_id: dict[ProductId, Product] = {}
        self._by_tenant_barcode: dict[tuple[str, str], Product] = {}

    async def get(self, product_id: ProductId) -> Product | None:
        return self._by_id.get(product_id)

    async def find_by_barcode(
        self,
        tenant_id: TenantId,
        barcode: Barcode,
    ) -> Product | None:
        return self._by_tenant_barcode.get((tenant_id.value, barcode.value))

    async def list_active(self, tenant_id: TenantId) -> list[Product]:
        from nexo_vending.domain.products.enums import ProductStatus

        return [
            product
            for product in self._by_id.values()
            if product.tenant_id == tenant_id and product.status == ProductStatus.ACTIVE
        ]

    async def save(self, product: Product) -> None:
        # Drop previous barcode index for this product id if barcode changed.
        for key, existing in list(self._by_tenant_barcode.items()):
            if existing.id == product.id:
                del self._by_tenant_barcode[key]
        self._by_id[product.id] = product
        self._by_tenant_barcode[(product.tenant_id.value, product.barcode.value)] = product


class InMemoryMachineRepository:
    def __init__(self) -> None:
        self._by_id: dict[MachineId, Machine] = {}
        self._by_tenant_code: dict[tuple[str, str], Machine] = {}

    async def get(self, machine_id: MachineId) -> Machine | None:
        return self._by_id.get(machine_id)

    async def find_by_code(self, tenant_id: TenantId, code) -> Machine | None:
        from nexo_vending.domain.machines.value_objects import MachineCode

        normalized = code if isinstance(code, MachineCode) else MachineCode(str(code))
        return self._by_tenant_code.get((tenant_id.value, normalized.value))

    async def get_by_code(self, code: str) -> Machine | None:
        # Backward-compatible helper for older tests; prefer find_by_code.
        from nexo_vending.domain.machines.value_objects import MachineCode

        normalized = MachineCode(code).value
        for (_tenant, machine_code), machine in self._by_tenant_code.items():
            if machine_code == normalized:
                return machine
        return None

    async def list_by_tenant(self, tenant_id: TenantId) -> list[Machine]:
        return [m for m in self._by_id.values() if m.tenant_id == tenant_id]

    async def save(self, machine: Machine) -> None:
        for key, existing in list(self._by_tenant_code.items()):
            if existing.id == machine.id:
                del self._by_tenant_code[key]
        self._by_id[machine.id] = machine
        self._by_tenant_code[(machine.tenant_id.value, machine.code.value)] = machine


class InMemoryReplenishmentRepository:
    def __init__(self) -> None:
        self._by_id: dict[ReplenishmentId, Replenishment] = {}
        self._by_key: dict[str, Replenishment] = {}

    async def get(self, replenishment_id: ReplenishmentId) -> Replenishment | None:
        return self._by_id.get(replenishment_id)

    async def find_by_idempotency_key(self, idempotency_key: str) -> Replenishment | None:
        return self._by_key.get(idempotency_key.strip())

    async def save(self, replenishment: Replenishment) -> None:
        self._by_id[replenishment.id] = replenishment
        self._by_key[replenishment.idempotency_key] = replenishment


class InMemoryInventoryRepository:
    def __init__(self) -> None:
        self._movements: list[InventoryMovement] = []

    async def list_movements_for_location(
        self,
        location: InventoryLocation,
        product_id: ProductId | None = None,
    ) -> list[InventoryMovement]:
        result: list[InventoryMovement] = []
        for movement in self._movements:
            if product_id is not None and movement.product_id != product_id:
                continue
            if (
                movement.source_location == location
                or movement.destination_location == location
            ):
                result.append(movement)
        return result

    async def expected_quantity(
        self,
        location: InventoryLocation,
        product_id: ProductId,
    ) -> int:
        return InventoryLedger.expected_quantity(
            self._movements,
            location=location,
            product_id=product_id,
        )

    async def record_movement(self, movement: InventoryMovement) -> None:
        InventoryLedger.ensure_can_apply(self._movements, movement)
        self._movements.append(movement)

    async def list_all(self) -> list[InventoryMovement]:
        return list(self._movements)


class InMemoryInventoryCountRepository:
    def __init__(self) -> None:
        self._by_id: dict = {}

    async def get(self, count_id):
        return self._by_id.get(count_id)

    async def save(self, count) -> None:
        self._by_id[count.id] = count


class InMemoryInventoryAvailability:
    def __init__(self, inventory: InMemoryInventoryRepository) -> None:
        self._inventory = inventory

    async def is_available(
        self,
        location: InventoryLocation,
        product_id: ProductId,
        quantity: Quantity,
    ) -> bool:
        stock = await self._inventory.expected_quantity(location, product_id)
        return stock >= quantity.value


class InMemoryProductLookup:
    def __init__(self, products: InMemoryProductRepository) -> None:
        self._products = products

    async def find_by_barcode(
        self,
        tenant_id: TenantId,
        barcode: Barcode,
    ) -> Product | None:
        return await self._products.find_by_barcode(tenant_id, barcode)


class InMemoryOperatorRepository:
    def __init__(self) -> None:
        self._by_id: dict[OperatorId, Operator] = {}
        self._by_principal: dict[tuple[str, str, str], Operator] = {}

    def _key(self, tenant_id: TenantId, principal: Principal) -> tuple[str, str, str]:
        return (tenant_id.value, principal.provider, principal.subject)

    async def get(self, operator_id: OperatorId) -> Operator | None:
        return self._by_id.get(operator_id)

    async def save(self, operator: Operator) -> None:
        self._by_id[operator.id] = operator
        self._by_principal[self._key(operator.tenant_id, operator.principal)] = operator

    async def find_by_principal(
        self,
        tenant_id: TenantId,
        principal: Principal,
    ) -> Operator | None:
        return self._by_principal.get(self._key(tenant_id, principal))
