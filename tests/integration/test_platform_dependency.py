import nexo_platform
from nexo_platform import (
    Database,
    DomainEvent,
    Tenant,
    TransactionalUnitOfWork,
    UnitOfWork,
)
from nexo_platform.transaction import SqlAlchemyTransactionalUnitOfWork

import nexo_vending


def test_platform_and_vending_import_together() -> None:
    assert nexo_vending.__version__
    assert nexo_platform.__name__ == "nexo_platform"
    assert Tenant is not None
    assert UnitOfWork is not None
    assert TransactionalUnitOfWork is not None
    assert SqlAlchemyTransactionalUnitOfWork is not None
    assert Database is not None
    assert DomainEvent is not None


def test_vending_uses_public_domain_event_only() -> None:
    event = DomainEvent(event_type="vending.smoke")
    assert event.event_id is not None
    assert event.payload == {}
