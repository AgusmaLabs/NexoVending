"""SQLAlchemy repository adapters sharing a Session."""

from __future__ import annotations

from nexo_platform.identity.authentication import Principal
from nexo_platform.transaction import TransactionConflict
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from nexo_vending.domain.common.ids import (
    MachineId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import Barcode
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.ledger import InventoryLedger
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.value_objects import MachineCode
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductStatus
from nexo_vending.domain.replenishment.entities import Replenishment
from nexo_vending.infrastructure.persistence.mappers import (
    machine_from_orm,
    machine_to_orm,
    movement_from_orm,
    movement_to_orm,
    operator_from_orm,
    operator_to_orm,
    product_from_orm,
    product_to_orm,
    replenishment_from_orm,
    replenishment_to_orm,
)
from nexo_vending.infrastructure.persistence.models import (
    InventoryMovementORM,
    MachineORM,
    MachineSlotORM,
    OperatorORM,
    ProductORM,
    ReplenishmentLineORM,
    ReplenishmentORM,
)


class SqlAlchemyProductRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get(self, product_id: ProductId) -> Product | None:
        row = self._session.get(ProductORM, product_id.value)
        return product_from_orm(row) if row else None

    async def find_by_barcode(self, tenant_id: TenantId, barcode: Barcode) -> Product | None:
        stmt = select(ProductORM).where(
            ProductORM.tenant_id == tenant_id.value,
            ProductORM.barcode == barcode.value,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return product_from_orm(row) if row else None

    async def list_active(self, tenant_id: TenantId) -> list[Product]:
        stmt = select(ProductORM).where(
            ProductORM.tenant_id == tenant_id.value,
            ProductORM.status == ProductStatus.ACTIVE.value,
        )
        return [product_from_orm(row) for row in self._session.execute(stmt).scalars()]

    async def save(self, product: Product) -> None:
        self._session.merge(product_to_orm(product))
        self._session.flush()


class SqlAlchemyOperatorRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get(self, operator_id: OperatorId) -> Operator | None:
        row = self._session.get(OperatorORM, operator_id.value)
        return operator_from_orm(row) if row else None

    async def save(self, operator: Operator) -> None:
        self._session.merge(operator_to_orm(operator))
        self._session.flush()

    async def find_by_principal(
        self,
        tenant_id: TenantId,
        principal: Principal,
    ) -> Operator | None:
        stmt = select(OperatorORM).where(
            OperatorORM.tenant_id == tenant_id.value,
            OperatorORM.principal_provider == principal.provider,
            OperatorORM.principal_subject == principal.subject,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return operator_from_orm(row) if row else None


class SqlAlchemyMachineRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get(self, machine_id: MachineId) -> Machine | None:
        row = self._session.get(MachineORM, machine_id.value)
        return machine_from_orm(row) if row else None

    async def find_by_code(self, tenant_id: TenantId, code) -> Machine | None:
        normalized = code if isinstance(code, MachineCode) else MachineCode(str(code))
        stmt = select(MachineORM).where(
            MachineORM.tenant_id == tenant_id.value,
            MachineORM.code == normalized.value,
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return machine_from_orm(row) if row else None

    async def list_by_tenant(self, tenant_id: TenantId) -> list[Machine]:
        stmt = select(MachineORM).where(MachineORM.tenant_id == tenant_id.value)
        return [machine_from_orm(row) for row in self._session.execute(stmt).scalars()]

    async def save(self, machine: Machine) -> None:
        existing = self._session.get(MachineORM, machine.id.value)
        if existing is not None:
            self._session.execute(
                delete(MachineSlotORM).where(MachineSlotORM.machine_id == machine.id.value)
            )
            self._session.expire(existing)
        self._session.merge(machine_to_orm(machine))
        self._session.flush()


class SqlAlchemyReplenishmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def get(self, replenishment_id: ReplenishmentId) -> Replenishment | None:
        row = self._session.get(ReplenishmentORM, replenishment_id.value)
        return replenishment_from_orm(row) if row else None

    async def find_by_idempotency_key(
        self,
        tenant_id: TenantId,
        idempotency_key: str,
    ) -> Replenishment | None:
        stmt = select(ReplenishmentORM).where(
            ReplenishmentORM.tenant_id == tenant_id.value,
            ReplenishmentORM.idempotency_key == idempotency_key.strip(),
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return replenishment_from_orm(row) if row else None

    async def save(self, replenishment: Replenishment) -> None:
        existing = self._session.get(ReplenishmentORM, replenishment.id.value)
        if existing is not None:
            if existing.version != replenishment.version:
                raise TransactionConflict(
                    f"stale replenishment version for {replenishment.id.value}"
                )
            self._session.execute(
                delete(ReplenishmentLineORM).where(
                    ReplenishmentLineORM.replenishment_id == replenishment.id.value
                )
            )
            self._session.expire(existing)
            orm = replenishment_to_orm(replenishment)
            orm.version = replenishment.version + 1
            self._session.merge(orm)
            replenishment.version = orm.version
            self._session.flush()
            return
        self._session.add(replenishment_to_orm(replenishment))
        self._session.flush()


class SqlAlchemyInventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    async def find_by_idempotency_key(
        self,
        tenant_id: TenantId,
        idempotency_key: str,
    ) -> InventoryMovement | None:
        stmt = select(InventoryMovementORM).where(
            InventoryMovementORM.tenant_id == tenant_id.value,
            InventoryMovementORM.idempotency_key == idempotency_key.strip(),
        )
        row = self._session.execute(stmt).scalar_one_or_none()
        return movement_from_orm(row) if row else None

    async def list_movements_for_location(
        self,
        location: InventoryLocation,
        product_id: ProductId | None = None,
    ) -> list[InventoryMovement]:
        src = and_(
            InventoryMovementORM.source_location_type == location.location_type.value,
            InventoryMovementORM.source_holder_id == location.holder_id,
            InventoryMovementORM.source_position_id == location.position_id,
        )
        dst = and_(
            InventoryMovementORM.destination_location_type == location.location_type.value,
            InventoryMovementORM.destination_holder_id == location.holder_id,
            InventoryMovementORM.destination_position_id == location.position_id,
        )
        stmt = select(InventoryMovementORM).where(or_(src, dst))
        if product_id is not None:
            stmt = stmt.where(InventoryMovementORM.product_id == product_id.value)
        stmt = stmt.order_by(InventoryMovementORM.occurred_at.asc())
        return [movement_from_orm(row) for row in self._session.execute(stmt).scalars()]

    async def expected_quantity(
        self,
        location: InventoryLocation,
        product_id: ProductId,
    ) -> int:
        movements = await self.list_movements_for_location(location, product_id)
        return InventoryLedger.expected_quantity(
            movements,
            location=location,
            product_id=product_id,
        )

    async def record_movement(self, movement: InventoryMovement) -> None:
        if movement.idempotency_key is not None:
            existing = await self.find_by_idempotency_key(
                movement.tenant_id,
                movement.idempotency_key,
            )
            if existing is not None:
                return
        if movement.source_location is not None:
            known = await self.list_movements_for_location(
                movement.source_location,
                movement.product_id,
            )
            InventoryLedger.ensure_can_apply(known, movement)
        self._session.add(movement_to_orm(movement))
        self._session.flush()
