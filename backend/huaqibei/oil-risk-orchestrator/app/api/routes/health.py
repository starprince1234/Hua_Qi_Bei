"""
健康检查路由
"""

from fastapi import APIRouter
from app.core.settings import settings

router = APIRouter(tags=["health"])


@router.get("/health", summary="服务健康检查")
async def health_check() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
