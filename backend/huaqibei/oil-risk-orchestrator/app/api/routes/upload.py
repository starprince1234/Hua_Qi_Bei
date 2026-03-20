"""文件上传路由。"""

from fastapi import APIRouter, File, UploadFile, Form
from fastapi.responses import JSONResponse

from app.schemas.report_schema import APIResponse
from app.schemas.upload_schema import UploadResult
from app.services.upload_service import UploadService
from app.core.errors import BusinessError, BusinessErrorCode
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/upload", tags=["Upload"])
_upload_service = UploadService()


def _parse_form_bool(raw_value: str | bool, field_name: str) -> bool:
    """Parse bool-like form values explicitly to avoid truthy string pitfalls."""
    if isinstance(raw_value, bool):
        return raw_value

    normalized = str(raw_value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False

    raise BusinessError(
        code=BusinessErrorCode.VALIDATION_ERROR,
        message=f"{field_name} must be a boolean value",
        status_code=400,
        details={"field": field_name, "value": raw_value},
    )


@router.post(
    "",
    summary="上传数据集文件（csv/xlsx/xls/parquet）",
    response_model=APIResponse,
    responses={
        400: {"model": APIResponse},
        413: {"model": APIResponse},
        415: {"model": APIResponse},
        500: {"model": APIResponse},
    },
)
async def upload_dataset(
    file: UploadFile = File(..., description="文件（csv/xlsx/parquet）"),
    dataset_type: str = Form(
        default="oil_price_factors",
        description="数据集类型",
    ),
    timezone: str = Form(default="UTC", description="时区"),
    frequency: str = Form(default="D", description="频率 D/W/M"),
    strict_mode: str | bool = Form(default="false", description="是否严格模式"),
    encoding: str = Form(default="utf-8", description="文件编码"),
) -> JSONResponse:
    """
    上传文件并返回校验与预览。
    """
    try:
        content = await file.read()
        internal_data_type = "oil_price" if dataset_type == "oil_price_factors" else dataset_type
        strict_mode_value = _parse_form_bool(strict_mode, "strict_mode")
        result: UploadResult = _upload_service.process_upload(
            filename=file.filename or "",
            content=content,
            data_type=internal_data_type,
            encoding=encoding,
            frequency=frequency,
            strict_mode=strict_mode_value,
        )
        return JSONResponse(content=APIResponse.ok(data=result.model_dump()).model_dump())
    except ValueError as exc:
        raise BusinessError(
            code=BusinessErrorCode.VALIDATION_ERROR,
            message=str(exc),
            status_code=400,
        )
