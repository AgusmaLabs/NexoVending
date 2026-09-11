from fastapi import APIRouter

from nexo_vending.api.health import router as health_router
from nexo_vending.api.routers.inventory import router as inventory_router
from nexo_vending.api.routers.machines import router as machines_router
from nexo_vending.api.routers.products import router as products_router
from nexo_vending.api.routers.replenishments import router as replenishments_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(machines_router)
api_router.include_router(products_router)
api_router.include_router(replenishments_router)
api_router.include_router(inventory_router)
