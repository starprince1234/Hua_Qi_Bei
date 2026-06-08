"""Factor history contribution API route."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse  # pyright: ignore[reportImplicitRelativeImport]
from app.services.intelligence_service import IntelligenceService  # pyright: ignore[reportImplicitRelativeImport]

router = APIRouter(prefix="/factors", tags=["Intelligence"])
_service = IntelligenceService()


@router.get("/history", summary="获取因子历史贡献", response_model=APIResponse)
async def get_factor_history(
    target: Annotated[str, Query(description="目标品种")] = "Brent",
    from_date: Annotated[str | None, Query(description="开始日期")] = None,
    to_date: Annotated[str | None, Query(description="结束日期")] = None,
    granularity: Annotated[str, Query(description="粒度")] = "month",
) -> JSONResponse:
    try:
        result = _service.get_factor_history(target, from_date, to_date, granularity)
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500, content=APIResponse.error(code=500, message=str(exc)).model_dump())
