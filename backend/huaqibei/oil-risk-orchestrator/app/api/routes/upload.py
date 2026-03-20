from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile, File

from app.api.dependencies import verify_api_key
from app.schemas.upload_schema import UploadResponse
from app.services.upload_service import save_upload
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["upload"])


@router.post("/upload", response_model=UploadResponse, summary="Upload data file for prediction")
async def upload_file(
    file: UploadFile = File(...),
    _: None = Depends(verify_api_key),
) -> UploadResponse:
    logger.info("Upload received", extra={"filename": file.filename, "content_type": file.content_type})
    result = await save_upload(file)
    return UploadResponse(
        success=True,
        data=result,
    )
