from enum import StrEnum


class ProductStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ProductUnit(StrEnum):
    UNIT = "UNIT"
    PACKAGE = "PACKAGE"
    BOTTLE = "BOTTLE"
    CAN = "CAN"
