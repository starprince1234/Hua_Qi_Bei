"""
全局自定义异常
"""

from fastapi import HTTPException, status


class OrchestratorError(Exception):
    """业务异常基类。"""

    def __init__(self, message: str, code: str = "ORCHESTRATOR_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class DataValidationError(OrchestratorError):
    """数据校验失败异常。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="DATA_VALIDATION_ERROR")


class ModelCallError(OrchestratorError):
    """模型调用失败异常。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="MODEL_CALL_ERROR")


class FeatureEngineeringError(OrchestratorError):
    """特征工程失败异常。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="FEATURE_ENGINEERING_ERROR")


class ReportGenerationError(OrchestratorError):
    """报告生成失败异常。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="REPORT_GENERATION_ERROR")


class UploadError(OrchestratorError):
    """文件上传处理失败异常。"""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="UPLOAD_ERROR")


def raise_http_400(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


def raise_http_404(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def raise_http_500(detail: str) -> None:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)
