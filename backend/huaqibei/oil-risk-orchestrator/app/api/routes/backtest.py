"""Backtest validation API routes."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse  # pyright: ignore[reportImplicitRelativeImport]
from app.services.intelligence_service import IntelligenceService  # pyright: ignore[reportImplicitRelativeImport]

router = APIRouter(prefix="/backtest", tags=["Intelligence"])
_service = IntelligenceService()


@router.get("/summary", summary="获取回测汇总指标", response_model=APIResponse)
async def get_backtest_summary(
    target: Annotated[str, Query(description="目标品种")] = "Brent",
) -> JSONResponse:
    try:
        result = _service.get_backtest_summary(target)
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500, content=APIResponse.error(code=500, message=str(exc)).model_dump())


@router.get("/series", summary="获取回测序列数据", response_model=APIResponse)
async def get_backtest_series(
    target: Annotated[str, Query(description="目标品种")] = "Brent",
) -> JSONResponse:
    try:
        result = _service.get_backtest_series(target)
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500, content=APIResponse.error(code=500, message=str(exc)).model_dump())


@router.get("/errors", summary="获取回测误差分布", response_model=APIResponse)
async def get_backtest_errors(
    target: Annotated[str, Query(description="目标品种")] = "Brent",
) -> JSONResponse:
    try:
        result = _service.get_backtest_errors(target)
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500, content=APIResponse.error(code=500, message=str(exc)).model_dump())
