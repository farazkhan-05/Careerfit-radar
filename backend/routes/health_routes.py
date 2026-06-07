from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.config import Settings, get_settings
from backend.database import get_db
from backend.models.api_schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live", response_model=HealthResponse)
def liveness() -> HealthResponse:
    return HealthResponse(status="ok", checks={"app": "ok"})


@router.get("/ready", response_model=HealthResponse)
def readiness(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthResponse:
    checks: dict[str, str] = {}
    status = "ok"
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "failed"
        status = "degraded"

    if settings.gemini_api_key and settings.gemini_llm_model and settings.gemini_embedding_model:
        checks["gemini"] = "configured"
    else:
        checks["gemini"] = "missing_configuration"
        status = "degraded"
    return HealthResponse(status=status, checks=checks)
