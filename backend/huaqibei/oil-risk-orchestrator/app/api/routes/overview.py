"""Overview API route for online intelligence dashboard data."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse
from app.services.intelligence_service import IntelligenceService

router = APIRouter(prefix="/overview", tags=["Intelligence"])
_service = IntelligenceService()


@router.get("", summary="获取在线工作台总览", response_model=APIResponse)
async def get_overview() -> JSONResponse:
    try:
        result = _service.get_overview()
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except Exception as exc:
        return JSONResponse(status_code=500, content=APIResponse.error(code=500, message=str(exc)).model_dump())
