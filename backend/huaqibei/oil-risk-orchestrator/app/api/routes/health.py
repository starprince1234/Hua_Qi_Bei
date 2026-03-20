from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.APP_NAME,
    }
