"""Shared fixtures for V9 HTTP API tests (PostgreSQL + Testcontainers)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from nexo_platform.authorization import AuthorizationService
from nexo_platform.entitlement import EntitlementService
from nexo_platform.identity.authentication import Principal
from nexo_platform.observability import Observability
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from nexo_vending.application.access_codes import (
    ALL_INVENTORY_PERMISSIONS,
    ALL_REPLENISHMENT_PERMISSIONS,
    ENTITLEMENT_INVENTORY,
    ENTITLEMENT_REPLENISHMENT,
)
from nexo_vending.domain.common.ids import (
    InventoryMovementId,
    MachineId,
    OperatorId,
    ProductId,
    TenantId,
)
from nexo_vending.domain.common.value_objects import Barcode, Quantity
from nexo_vending.domain.identity.entities import Operator
from nexo_vending.domain.identity.enums import OperatorRole
from nexo_vending.domain.inventory.entities import InventoryMovement
from nexo_vending.domain.inventory.enums import InventoryMovementType, InventoryReferenceType
from nexo_vending.domain.inventory.locations import InventoryLocation
from nexo_vending.domain.machines.assignment import MachineAssignment
from nexo_vending.domain.machines.entities import Machine
from nexo_vending.domain.machines.enums import MachineType
from nexo_vending.domain.machines.value_objects import SellingPrice
from nexo_vending.domain.products.entities import Product
from nexo_vending.infrastructure.persistence import VendingPersistence, transactional_uow
from nexo_vending.main import create_app
from nexo_vending.versioning import API_PREFIX

ROOT = Path(__file__).resolve().parents[2]


def api(path: str) -> str:
    """Build a versioned business-API path (health stays unversioned)."""
    if not path.startswith("/"):
        raise ValueError(f"path must be absolute, got {path!r}")
    return f"{API_PREFIX}{path}"

PLATFORM_IDEMPOTENCY_DDL = """
CREATE TABLE IF NOT EXISTS platform_idempotency_records (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    operation VARCHAR(128) NOT NULL,
    idempotency_key VARCHAR(128) NOT NULL,
    request_hash VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL,
    result JSONB,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT uq_platform_idempotency_tenant_operation_key
        UNIQUE (tenant_id, operation, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_platform_idempotency_expires_at
    ON platform_idempotency_records (expires_at);
"""


@pytest.fixture()
def migrated_engine(postgres_url: str):
    engine = create_engine(postgres_url, pool_pre_ping=True)
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", postgres_url)
    command.upgrade(cfg, "head")
    with engine.begin() as conn:
        conn.execute(text(PLATFORM_IDEMPOTENCY_DDL))
    try:
        yield engine
    finally:
        command.downgrade(cfg, "base")
        with engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS platform_idempotency_records"))
        engine.dispose()


@pytest.fixture()
def session_factory(migrated_engine) -> sessionmaker[Session]:
    return sessionmaker(bind=migrated_engine, autoflush=False, autocommit=False)


def auth_headers(
    *,
    tenant: str,
    provider: str,
    subject: str,
    idempotency_key: str | None = None,
    request_id: str | None = None,
) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer principal/{provider}/{subject}",
        "X-Tenant-Id": tenant,
    }
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    if request_id is not None:
        headers["X-Request-Id"] = request_id
    return headers


def grant_all(
    authz: AuthorizationService,
    ents: EntitlementService,
    *,
    tenant: str,
    actor_id: str,
) -> None:
    ents.grant(tenant, ENTITLEMENT_REPLENISHMENT.code)
    ents.grant(tenant, ENTITLEMENT_INVENTORY.code)
    for permission in (*ALL_REPLENISHMENT_PERMISSIONS, *ALL_INVENTORY_PERMISSIONS):
        authz.register(actor_id, permission.code, tenant_id=tenant)


@pytest.fixture()
def api_world(session_factory) -> Iterator[dict]:
    """Seed tenant-a replenisher + admin, machine, product, inventory stock."""
    session = session_factory()
    try:
        import asyncio

        world = asyncio.run(_seed(session))
    finally:
        session.close()

    authz = AuthorizationService()
    ents = EntitlementService()
    grant_all(
        authz,
        ents,
        tenant="tenant-a",
        actor_id=f"google:{world['replenisher_subject']}",
    )
    grant_all(
        authz,
        ents,
        tenant="tenant-a",
        actor_id=f"google:{world['admin_subject']}",
    )
    grant_all(
        authz,
        ents,
        tenant="tenant-b",
        actor_id=f"google:{world['tenant_b_subject']}",
    )

    app = create_app(
        authorization=authz,
        entitlements=ents,
        observability=Observability.memory(),
    )
    app.state.session_factory = session_factory
    client = TestClient(app, raise_server_exceptions=False)
    world["client"] = client
    world["app"] = app
    world["authz"] = authz
    world["ents"] = ents
    world["session_factory"] = session_factory
    yield world


async def _seed(session: Session) -> dict:
    async with transactional_uow(session) as uow:
        p = VendingPersistence.for_session(uow.session)
        tenant = TenantId("tenant-a")
        product = Product.create(
            product_id=ProductId.new(),
            tenant_id=tenant,
            barcode=Barcode("7800001"),
            name="Coca",
            created_at=datetime(2026, 9, 10, tzinfo=UTC),
        )
        await p.products.save(product)

        machine = Machine.create(
            machine_id=MachineId.new(),
            tenant_id=tenant,
            code="MIX-001",
            name="Lobby",
            machine_type=MachineType.SNACK,
            created_at=datetime(2026, 9, 10, tzinfo=UTC),
        )
        machine.add_slot(
            slot_number=7,
            capacity=10,
            selling_price=SellingPrice(amount=Decimal("1500")),
        )
        await p.machines.save(machine)

        replenisher = Operator.provision(
            operator_id=OperatorId.new(),
            tenant_id=tenant,
            principal=Principal(provider="google", subject="replenisher-1"),
            role=OperatorRole.OPERATOR,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
        replenisher.activate()
        await p.operators.save(replenisher)
        await p.assignments.save(
            MachineAssignment.create(
                tenant_id=tenant,
                replenisher_id=replenisher.id,
                machine_id=machine.id,
                valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

        admin = Operator.provision(
            operator_id=OperatorId.new(),
            tenant_id=tenant,
            principal=Principal(provider="google", subject="admin-1"),
            role=OperatorRole.ADMIN,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
        admin.activate()
        await p.operators.save(admin)

        await p.inventory.record_movement(
            InventoryMovement(
                id=InventoryMovementId.new(),
                tenant_id=tenant,
                product_id=product.id,
                quantity=Quantity(50),
                movement_type=InventoryMovementType.ASSIGNMENT,
                reference_type=InventoryReferenceType.ASSIGNMENT,
                reference_id="seed",
                occurred_at=datetime(2026, 9, 10, 8, 0, tzinfo=UTC),
                actor_id=admin.id,
                destination_location=InventoryLocation.replenisher(replenisher.id),
                idempotency_key="tenant-a:seed",
            )
        )

        # Tenant B machine + operator for isolation tests
        tenant_b = TenantId("tenant-b")
        machine_b = Machine.create(
            machine_id=MachineId.new(),
            tenant_id=tenant_b,
            code="MIX-B",
            name="Other",
            machine_type=MachineType.SNACK,
            created_at=datetime(2026, 9, 10, tzinfo=UTC),
        )
        machine_b.add_slot(slot_number=1, capacity=5, selling_price=SellingPrice(amount=Decimal("1")))
        await p.machines.save(machine_b)
        op_b = Operator.provision(
            operator_id=OperatorId.new(),
            tenant_id=tenant_b,
            principal=Principal(provider="google", subject="op-b"),
            role=OperatorRole.OPERATOR,
            valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        )
        op_b.activate()
        await p.operators.save(op_b)
        await p.assignments.save(
            MachineAssignment.create(
                tenant_id=tenant_b,
                replenisher_id=op_b.id,
                machine_id=machine_b.id,
                valid_from=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

        return {
            "product_id": str(product.id.value),
            "machine_id": str(machine.id.value),
            "slot_id": str(machine.slots[0].id.value),
            "machine_b_id": str(machine_b.id.value),
            "replenisher_id": str(replenisher.id.value),
            "admin_id": str(admin.id.value),
            "replenisher_subject": "replenisher-1",
            "admin_subject": "admin-1",
            "tenant_b_subject": "op-b",
        }


def replenisher_headers(world: dict, *, key: str | None = None) -> dict[str, str]:
    return auth_headers(
        tenant="tenant-a",
        provider="google",
        subject=world["replenisher_subject"],
        idempotency_key=key,
    )


def admin_headers(world: dict, *, key: str | None = None) -> dict[str, str]:
    return auth_headers(
        tenant="tenant-a",
        provider="google",
        subject=world["admin_subject"],
        idempotency_key=key,
    )
