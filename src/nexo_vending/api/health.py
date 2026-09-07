from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.engine import Engine

from nexo_vending.api.deps import get_db_engine
from nexo_vending.application import health as health_app

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return health_app.liveness()


@router.get("/health/ready")
def health_ready(engine: Engine = Depends(get_db_engine)) -> dict[str, str]:
    try:
        return health_app.readiness(engine)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
