"""Composition helpers: Session + Platform UoW + Vending repositories."""

from __future__ import annotations

from dataclasses import dataclass

from nexo_platform.transaction import SqlAlchemyTransactionalUnitOfWork
from sqlalchemy.orm import Session

from nexo_vending.infrastructure.persistence.repositories import (
    SqlAlchemyInventoryRepository,
    SqlAlchemyMachineAssignmentRepository,
    SqlAlchemyMachineRepository,
    SqlAlchemyOperatorRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyReplenishmentRepository,
)


@dataclass(slots=True)
class VendingPersistence:
    """Product repositories bound to one Session (use inside Platform UoW)."""

    session: Session
    products: SqlAlchemyProductRepository
    machines: SqlAlchemyMachineRepository
    operators: SqlAlchemyOperatorRepository
    replenishments: SqlAlchemyReplenishmentRepository
    inventory: SqlAlchemyInventoryRepository
    assignments: SqlAlchemyMachineAssignmentRepository

    @classmethod
    def for_session(cls, session: Session) -> VendingPersistence:
        return cls(
            session=session,
            products=SqlAlchemyProductRepository(session),
            machines=SqlAlchemyMachineRepository(session),
            operators=SqlAlchemyOperatorRepository(session),
            replenishments=SqlAlchemyReplenishmentRepository(session),
            inventory=SqlAlchemyInventoryRepository(session),
            assignments=SqlAlchemyMachineAssignmentRepository(session),
        )


def transactional_uow(session: Session) -> SqlAlchemyTransactionalUnitOfWork:
    """Platform public UoW; does not create a second Session."""
    return SqlAlchemyTransactionalUnitOfWork(session)
