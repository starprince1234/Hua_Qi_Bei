from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_api_key
from app.schemas.report_schema import ReportResponse
from app.services.report_service import generate_report
from app.core.errors import NotFoundError
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["report"])


@router.get("/report/{file_id}", response_model=ReportResponse, summary="Retrieve prediction report")
async def get_report(
    file_id: str,
    style: str = "general",
    _: None = Depends(verify_api_key),
) -> ReportResponse:
    logger.info("Report request", extra={"file_id": file_id, "style": style})
    report = await generate_report(file_id=file_id, style=style)
    if report is None:
        raise NotFoundError(f"No report found for file_id={file_id}")
    return report
