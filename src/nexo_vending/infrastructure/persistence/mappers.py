"""Domain ↔ ORM mappers."""

from __future__ import annotations

from decimal import Decimal

from nexo_platform.identity.authentication import Principal

from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    MachineId,
    OperatorId,
    ProductId,
    ReplenishmentId,
    ReplenishmentLineId,
    SlotId,
    TenantId,
    UserId,
)
from nexo_vending.domain.common.value_objects import (
    Barcode,
    GeoLocation,
    Quantity,
    SignedQuantity,
)
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole, OperatorStatus
from nexo_vending.domain.identity.value_objects import Email, ValidityPeriod
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import (
    InventoryLocationType,
    InventoryMovementType,
    InventoryReferenceType,
)
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.assignment import (
    MachineAssignment,
    MachineAssignmentId,
    MachineAssignmentStatus,
)
from nexo_vending.domain.machines.entities import Machine, MachineSlot
from nexo_vending.domain.machines.enums import MachineStatus, MachineType, SlotStatus
from nexo_vending.domain.machines.value_objects import MachineCode, MachineLocation, SellingPrice
from nexo_vending.domain.products.entities import Product
from nexo_vending.domain.products.enums import ProductStatus, ProductUnit
from nexo_vending.domain.products.value_objects import ProductName
from nexo_vending.domain.replenishment.entities import Replenishment, ReplenishmentLine
from nexo_vending.domain.replenishment.enums import (
    LineResolutionStatus,
    ReplacementReason,
    ReplenishmentStatus,
)
from nexo_vending.infrastructure.persistence.models import (
    InventoryMovementORM,
    MachineAssignmentORM,
    MachineORM,
    MachineSlotORM,
    OperatorORM,
    ProductORM,
    ReplenishmentLineORM,
    ReplenishmentORM,
)


def _location_to_parts(
    location: InventoryLocation | None,
) -> tuple[str | None, str | None, str | None]:
    if location is None:
        return None, None, None
    return location.location_type.value, location.holder_id, location.position_id


def _parts_to_location(
    location_type: str | None,
    holder_id: str | None,
    position_id: str | None,
) -> InventoryLocation | None:
    if location_type is None or holder_id is None:
        return None
    return InventoryLocation(
        location_type=InventoryLocationType(location_type),
        holder_id=holder_id,
        position_id=position_id,
    )


def product_to_orm(product: Product) -> ProductORM:
    return ProductORM(
        id=product.id.value,
        tenant_id=product.tenant_id.value,
        barcode=product.barcode.value,
        name=product.name.value,
        unit=product.unit.value,
        low_stock_threshold=product.low_stock_threshold,
        status=product.status.value,
        created_at=product.created_at,
        updated_at=product.updated_at,
        description=product.description,
        brand=product.brand,
        category=product.category,
    )


def product_from_orm(row: ProductORM) -> Product:
    return Product(
        id=ProductId(row.id),
        tenant_id=TenantId(row.tenant_id),
        barcode=Barcode(row.barcode),
        name=ProductName(row.name),
        unit=ProductUnit(row.unit),
        low_stock_threshold=row.low_stock_threshold,
        status=ProductStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        description=row.description,
        brand=row.brand,
        category=row.category,
    )


def operator_to_orm(operator: Operator) -> OperatorORM:
    return OperatorORM(
        id=operator.id.value,
        tenant_id=operator.tenant_id.value,
        principal_provider=operator.principal.provider,
        principal_subject=operator.principal.subject,
        role=operator.role.value,
        status=operator.status.value,
        email=operator.email.value if operator.email else None,
        display_name=operator.display_name,
        valid_from=operator.validity_period.valid_from,
        valid_until=operator.validity_period.valid_until,
    )


def operator_from_orm(row: OperatorORM) -> Operator:
    return Operator(
        id=OperatorId(row.id),
        tenant_id=TenantId(row.tenant_id),
        principal=Principal(provider=row.principal_provider, subject=row.principal_subject),
        role=OperatorRole(row.role),
        status=OperatorStatus(row.status),
        validity_period=ValidityPeriod(
            valid_from=row.valid_from,
            valid_until=row.valid_until,
        ),
        email=Email(row.email) if row.email else None,
        display_name=row.display_name,
    )


def machine_to_orm(machine: Machine) -> MachineORM:
    location = machine.location
    return MachineORM(
        id=machine.id.value,
        tenant_id=machine.tenant_id.value,
        code=machine.code.value,
        name=machine.name,
        type=machine.type.value,
        status=machine.status.value,
        created_at=machine.created_at,
        updated_at=machine.updated_at,
        location_label=location.address if location else None,
        location_latitude=location.latitude if location else None,
        location_longitude=location.longitude if location else None,
        sii_id=machine.sii_id,
        version=getattr(machine, "version", 1),
        slots=[
            MachineSlotORM(
                id=slot.id.value,
                machine_id=machine.id.value,
                slot_number=slot.slot_number,
                capacity=slot.capacity,
                status=slot.status.value,
                preferred_product_id=(
                    slot.preferred_product_id.value if slot.preferred_product_id else None
                ),
                selling_price_amount=(
                    slot.selling_price.amount if slot.selling_price else None
                ),
                selling_price_currency=(
                    slot.selling_price.currency if slot.selling_price else None
                ),
            )
            for slot in machine.slots
        ],
    )


def machine_from_orm(row: MachineORM) -> Machine:
    location = None
    if row.location_label is not None:
        location = MachineLocation(
            address=row.location_label,
            latitude=float(row.location_latitude or 0.0),
            longitude=float(row.location_longitude or 0.0),
        )
    machine = Machine(
        id=MachineId(row.id),
        tenant_id=TenantId(row.tenant_id),
        code=MachineCode(row.code),
        name=row.name,
        type=MachineType(row.type),
        status=MachineStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        location=location,
        sii_id=row.sii_id,
        _slots=[],
    )
    for slot_row in row.slots:
        price = None
        if slot_row.selling_price_amount is not None:
            price = SellingPrice(
                amount=Decimal(slot_row.selling_price_amount),
                currency=slot_row.selling_price_currency or "CLP",
            )
        machine._slots.append(
            MachineSlot(
                id=SlotId(slot_row.id),
                slot_number=slot_row.slot_number,
                capacity=slot_row.capacity,
                status=SlotStatus(slot_row.status),
                preferred_product_id=(
                    ProductId(slot_row.preferred_product_id)
                    if slot_row.preferred_product_id
                    else None
                ),
                selling_price=price,
            )
        )
    return machine


def replenishment_to_orm(replenishment: Replenishment) -> ReplenishmentORM:
    return ReplenishmentORM(
        id=replenishment.id.value,
        tenant_id=replenishment.tenant_id.value,
        operator_id=replenishment.operator_id.value,
        machine_id=replenishment.machine_id.value,
        machine_type=replenishment.machine_type.value,
        started_at=replenishment.started_at,
        completed_at=replenishment.completed_at,
        status=replenishment.status.value,
        idempotency_key=replenishment.idempotency_key,
        latitude=replenishment.location.latitude,
        longitude=replenishment.location.longitude,
        accuracy=replenishment.location.accuracy,
        version=replenishment.version,
        lines=[
            ReplenishmentLineORM(
                id=line.id.value,
                replenishment_id=replenishment.id.value,
                machine_position_id=line.machine_position_id.value,
                product_id=line.product_id.value if line.product_id is not None else None,
                quantity=line.quantity.value,
                unit_price=line.unit_price,
                occurred_at=line.occurred_at,
                product_description_snapshot=line.product_description_snapshot,
                preferred_product_id_snapshot=(
                    line.preferred_product_id_snapshot.value
                    if line.preferred_product_id_snapshot
                    else None
                ),
                replacement_reason=(
                    line.replacement_reason.value if line.replacement_reason else None
                ),
                barcode_scanned=line.barcode_scanned.value if line.barcode_scanned else None,
                manual_description=line.manual_description,
                resolution_status=line.resolution_status.value,
                resolved_at=line.resolved_at,
                resolved_by_operator_id=(
                    line.resolved_by_operator_id.value
                    if line.resolved_by_operator_id is not None
                    else None
                ),
            )
            for line in replenishment.lines
        ],
    )


def replenishment_from_orm(row: ReplenishmentORM) -> Replenishment:
    replenishment = Replenishment(
        id=ReplenishmentId(row.id),
        tenant_id=TenantId(row.tenant_id),
        operator_id=UserId(row.operator_id),
        machine_id=MachineId(row.machine_id),
        machine_type=MachineType(row.machine_type),
        started_at=row.started_at,
        location=GeoLocation(
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            accuracy=float(row.accuracy),
        ),
        idempotency_key=row.idempotency_key,
        status=ReplenishmentStatus(row.status),
        completed_at=row.completed_at,
        version=row.version,
        _lines=[],
    )
    for line_row in row.lines:
        replenishment._lines.append(
            ReplenishmentLine(
                id=ReplenishmentLineId(line_row.id),
                machine_position_id=SlotId(line_row.machine_position_id),
                product_id=(
                    ProductId(line_row.product_id) if line_row.product_id is not None else None
                ),
                quantity=SignedQuantity(line_row.quantity),
                unit_price=Decimal(line_row.unit_price),
                occurred_at=line_row.occurred_at,
                product_description_snapshot=line_row.product_description_snapshot,
                resolution_status=LineResolutionStatus(line_row.resolution_status),
                preferred_product_id_snapshot=(
                    ProductId(line_row.preferred_product_id_snapshot)
                    if line_row.preferred_product_id_snapshot
                    else None
                ),
                replacement_reason=(
                    ReplacementReason(line_row.replacement_reason)
                    if line_row.replacement_reason
                    else None
                ),
                barcode_scanned=(
                    Barcode(line_row.barcode_scanned) if line_row.barcode_scanned else None
                ),
                manual_description=line_row.manual_description,
                resolved_at=line_row.resolved_at,
                resolved_by_operator_id=(
                    OperatorId(line_row.resolved_by_operator_id)
                    if line_row.resolved_by_operator_id is not None
                    else None
                ),
            )
        )
    return replenishment


def movement_to_orm(movement: InventoryMovement) -> InventoryMovementORM:
    src_type, src_holder, src_pos = _location_to_parts(movement.source_location)
    dst_type, dst_holder, dst_pos = _location_to_parts(movement.destination_location)
    return InventoryMovementORM(
        id=movement.id.value,
        tenant_id=movement.tenant_id.value,
        product_id=movement.product_id.value,
        quantity=movement.quantity.value,
        movement_type=movement.movement_type.value,
        reference_type=movement.reference_type.value,
        reference_id=movement.reference_id,
        occurred_at=movement.occurred_at,
        actor_id=movement.actor_id.value,
        source_location_type=src_type,
        source_holder_id=src_holder,
        source_position_id=src_pos,
        destination_location_type=dst_type,
        destination_holder_id=dst_holder,
        destination_position_id=dst_pos,
        idempotency_key=movement.idempotency_key,
    )


def movement_from_orm(row: InventoryMovementORM) -> InventoryMovement:
    return InventoryMovement(
        id=InventoryMovementId(row.id),
        tenant_id=TenantId(row.tenant_id),
        product_id=ProductId(row.product_id),
        quantity=Quantity(row.quantity),
        movement_type=InventoryMovementType(row.movement_type),
        reference_type=InventoryReferenceType(row.reference_type),
        reference_id=row.reference_id,
        occurred_at=row.occurred_at,
        actor_id=UserId(row.actor_id),
        source_location=_parts_to_location(
            row.source_location_type,
            row.source_holder_id,
            row.source_position_id,
        ),
        destination_location=_parts_to_location(
            row.destination_location_type,
            row.destination_holder_id,
            row.destination_position_id,
        ),
        idempotency_key=row.idempotency_key,
    )


def assignment_to_orm(assignment: MachineAssignment) -> MachineAssignmentORM:
    return MachineAssignmentORM(
        id=assignment.id.value,
        tenant_id=assignment.tenant_id.value,
        replenisher_id=assignment.replenisher_id.value,
        machine_id=assignment.machine_id.value,
        status=assignment.status.value,
        valid_from=assignment.validity_period.valid_from,
        valid_until=assignment.validity_period.valid_until,
    )


def assignment_from_orm(row: MachineAssignmentORM) -> MachineAssignment:
    return MachineAssignment(
        id=MachineAssignmentId(row.id),
        tenant_id=TenantId(row.tenant_id),
        replenisher_id=OperatorId(row.replenisher_id),
        machine_id=MachineId(row.machine_id),
        validity_period=ValidityPeriod(
            valid_from=row.valid_from,
            valid_until=row.valid_until,
        ),
        status=MachineAssignmentStatus(row.status),
    )
