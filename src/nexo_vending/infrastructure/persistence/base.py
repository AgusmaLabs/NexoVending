"""Vending DeclarativeBase — never inherit Platform ORM Base."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
