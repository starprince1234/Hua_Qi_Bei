from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.core.settings import get_settings

router = APIRouter(prefix="/model-placeholder", tags=["model-placeholder"])


@router.get("/status", summary="Model service placeholder status")
async def model_placeholder_status() -> dict:
    """
    Placeholder endpoint used when the real model service is unavailable.
    Returns a mock status so the orchestrator and frontend can be tested end-to-end.
    """
    settings = get_settings()
    return {
        "status": "placeholder",
        "model_service_url": settings.MODEL_SERVICE_URL,
        "message": "Model service placeholder active. Real predictions unavailable.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mock_capabilities": {
            "predict": True,
            "shap_values": True,
            "quantiles": True,
        },
    }
