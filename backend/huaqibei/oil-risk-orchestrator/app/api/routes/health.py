"""
健康检查路由

职责：
    - 提供系统存活检查和就绪检查端点
    - 检查云端模型服务可达性

禁止：
    - 在此文件中写业务逻辑
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", summary="存活检查")
async def liveness() -> JSONResponse:
    """
    Liveness Probe：服务是否运行。

    Returns:
        200 OK with status=alive。
    """
    return JSONResponse(
        content=APIResponse.ok(
            data={"status": "ok", "version": settings.APP_VERSION}
        ).model_dump()
    )
