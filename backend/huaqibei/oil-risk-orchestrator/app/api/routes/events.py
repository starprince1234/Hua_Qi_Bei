"""News events API route."""

from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse  # pyright: ignore[reportImplicitRelativeImport]
from app.services.intelligence_service import IntelligenceService  # pyright: ignore[reportImplicitRelativeImport]

router = APIRouter(prefix="/events", tags=["Intelligence"])
_service = IntelligenceService()


@router.get("", summary="获取新闻事件列表", response_model=APIResponse)
async def get_events(
    impact_direction: Annotated[str | None, Query(description="影响方向")] = None,
    impact_level: Annotated[str | None, Query(description="影响强度")] = None,
    source: Annotated[str | None, Query(description="数据来源")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    from_date: Annotated[str | None, Query(description="开始日期")] = None,
    to_date: Annotated[str | None, Query(description="结束日期")] = None,
    keyword: Annotated[str | None, Query(description="关键词")] = None,
) -> JSONResponse:
    try:
        filters: dict[str, str | int | None] = {
            key: value
            for key, value in {
                "impact_direction": impact_direction,
                "impact_level": impact_level,
                "source": source,
                "limit": limit,
                "offset": offset,
                "from_date": from_date,
                "to_date": to_date,
                "keyword": keyword,
            }.items()
            if value is not None
        }
        result = _service.get_events(filters)
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=APIResponse.error(code=500, message=str(exc)).model_dump(),
        )
