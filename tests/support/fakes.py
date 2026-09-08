"""In-memory fakes for domain/application tests (not production adapters)."""

from __future__ import annotations

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import (
    MachineId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    TenantId,
    UserId,
)
from nexo_vending.domain.common.value_objects import Barcode, Quantity
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.replenishment.entities import Replenishment


class InMemoryProductRepository:
    def __init__(self) -> None:
        self._by_id: dict[ProductId, Product] = {}
        self._by_barcode: dict[str, Product] = {}

    async def get(self, product_id: ProductId) -> Product | None:
        return self._by_id.get(product_id)

    async def find_by_barcode(self, barcode: Barcode) -> Product | None:
        return self._by_barcode.get(barcode.value)

    async def save(self, product: Product) -> None:
        self._by_id[product.id] = product
        self._by_barcode[product.barcode.value] = product


class InMemoryMachineRepository:
    def __init__(self) -> None:
        self._by_id: dict[MachineId, Machine] = {}
        self._by_code: dict[str, Machine] = {}

    async def get(self, machine_id: MachineId) -> Machine | None:
        return self._by_id.get(machine_id)

    async def get_by_code(self, code: str) -> Machine | None:
        return self._by_code.get(code.strip())

    async def save(self, machine: Machine) -> None:
        self._by_id[machine.id] = machine
        self._by_code[machine.code] = machine


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

    async def list_movements(
        self,
        operator_id: UserId,
        product_id: ProductId,
    ) -> list[InventoryMovement]:
        return [
            m
            for m in self._movements
            if m.operator_id == operator_id and m.product_id == product_id
        ]

    async def get_stock(self, operator_id: UserId, product_id: ProductId) -> int:
        return InventoryLedger.stock_for(
            self._movements,
            operator_id=operator_id,
            product_id=product_id,
        )

    async def record_movement(self, movement: InventoryMovement) -> None:
        InventoryLedger.ensure_can_apply(self._movements, movement)
        self._movements.append(movement)


class InMemoryProductLookup:
    def __init__(self, products: InMemoryProductRepository) -> None:
        self._products = products

    async def find_by_barcode(self, barcode: Barcode) -> Product | None:
        return await self._products.find_by_barcode(barcode)


class InMemoryInventoryAvailability:
    def __init__(self, inventory: InMemoryInventoryRepository) -> None:
        self._inventory = inventory

    async def is_available(
        self,
        operator_id: UserId,
        product_id: ProductId,
        quantity: Quantity,
    ) -> bool:
        stock = await self._inventory.get_stock(operator_id, product_id)
        return stock >= quantity.value


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
