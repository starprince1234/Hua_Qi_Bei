"""
文件上传路由
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.dependencies import get_upload_service
from app.core.settings import settings
from app.schemas.upload_schema import UploadResponse, UploadStatusResponse
from app.services.upload_service import UploadService

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=UploadResponse, summary="上传历史油价数据文件")
async def upload_file(
    file: UploadFile = File(...),
    upload_svc: UploadService = Depends(get_upload_service),
) -> UploadResponse:
    # 文件大小限制
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过 {settings.MAX_FILE_SIZE_MB} MB 限制",
        )

    try:
        upload_id, row_count, report, _ = upload_svc.parse_and_validate(
            filename=file.filename or "upload.csv",
            content=content,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    return UploadResponse(
        upload_id=upload_id,
        filename=file.filename or "",
        row_count=row_count,
        passed_validation=report.passed,
        errors=report.errors,
        warnings=report.warnings,
        repair_log=report.repair_log,
    )


@router.get("/{upload_id}/status", response_model=UploadStatusResponse, summary="查询上传状态")
async def get_upload_status(
    upload_id: str,
    upload_svc: UploadService = Depends(get_upload_service),
) -> UploadStatusResponse:
    info = upload_svc.get_status(upload_id)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"上传 ID {upload_id} 不存在或已过期",
        )
    return UploadStatusResponse(**info)
