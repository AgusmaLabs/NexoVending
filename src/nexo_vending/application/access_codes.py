"""Vending-owned permission and entitlement codes (Platform mechanism)."""

from __future__ import annotations

from nexo_platform.authorization import Permission
from nexo_platform.entitlement import Entitlement

# Permissions — "can this principal execute the operation?"
REPLENISHMENT_CREATE = Permission("replenishment.create")
REPLENISHMENT_READ = Permission("replenishment.read")
REPLENISHMENT_ADD_LINE = Permission("replenishment.add_line")
REPLENISHMENT_COMPLETE = Permission("replenishment.complete")
REPLENISHMENT_CANCEL = Permission("replenishment.cancel")

MACHINE_READ = Permission("machine.read")
MACHINE_RESOLVE = Permission("machine.resolve")
PRODUCT_READ = Permission("product.read")

INVENTORY_ASSIGN = Permission("inventory.assign")
INVENTORY_RETURN = Permission("inventory.return")
INVENTORY_ADJUST = Permission("inventory.adjust")
INVENTORY_LOSS = Permission("inventory.loss")
INVENTORY_READ = Permission("inventory.read")

# Entitlements — "does this tenant have the product capability?"
ENTITLEMENT_REPLENISHMENT = Entitlement("vending.replenishment")
ENTITLEMENT_INVENTORY = Entitlement("vending.inventory")

ALL_REPLENISHMENT_PERMISSIONS = (
    REPLENISHMENT_CREATE,
    REPLENISHMENT_READ,
    REPLENISHMENT_ADD_LINE,
    REPLENISHMENT_COMPLETE,
    REPLENISHMENT_CANCEL,
    MACHINE_READ,
    MACHINE_RESOLVE,
    PRODUCT_READ,
)

ALL_INVENTORY_PERMISSIONS = (
    INVENTORY_ASSIGN,
    INVENTORY_RETURN,
    INVENTORY_ADJUST,
    INVENTORY_LOSS,
    INVENTORY_READ,
)
