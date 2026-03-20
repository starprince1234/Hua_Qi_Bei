"""
模型服务占位路由

提供模型服务连通性检查与基础信息查询。
"""

from fastapi import APIRouter, Depends

from app.api.dependencies import get_model_client
from app.core.constants import SUPPORTED_HORIZONS
from app.core.settings import settings
from app.schemas.model_service_schema import ModelServiceHealthResponse, ModelServiceInfoResponse
from app.services.model_client import ModelClient

router = APIRouter(prefix="/model-service", tags=["model-service"])


@router.get("/health", response_model=ModelServiceHealthResponse, summary="模型服务健康检查")
async def model_service_health(
    client: ModelClient = Depends(get_model_client),
) -> ModelServiceHealthResponse:
    import time

    start = time.perf_counter()
    reachable = await client.health_check()
    latency_ms = (time.perf_counter() - start) * 1000

    return ModelServiceHealthResponse(
        reachable=reachable,
        model_id=settings.MODEL_API_MODEL_ID,
        latency_ms=round(latency_ms, 2),
    )


@router.get("/info", response_model=ModelServiceInfoResponse, summary="模型服务基础信息")
async def model_service_info(
    client: ModelClient = Depends(get_model_client),
) -> ModelServiceInfoResponse:
    return ModelServiceInfoResponse(
        model_id=settings.MODEL_API_MODEL_ID,
        api_url=settings.MODEL_API_URL,
        mode=client.mode,
        supported_horizons=SUPPORTED_HORIZONS,
    )
