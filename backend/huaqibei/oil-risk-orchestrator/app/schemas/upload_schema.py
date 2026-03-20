"""
上传相关 Schema
"""

from pydantic import BaseModel, Field
from typing import Optional


class UploadResponse(BaseModel):
    """文件上传响应。"""

    upload_id: str = Field(..., description="上传文件唯一标识")
    filename: str = Field(..., description="原始文件名")
    row_count: int = Field(..., description="解析到的数据行数")
    passed_validation: bool = Field(..., description="是否通过数据校验")
    errors: list[str] = Field(default_factory=list, description="校验错误信息")
    warnings: list[str] = Field(default_factory=list, description="校验警告信息")
    repair_log: list[dict] = Field(default_factory=list, description="修复日志")


class UploadStatusResponse(BaseModel):
    """文件上传状态查询响应。"""

    upload_id: str
    status: str = Field(..., description="状态：pending / ready / expired")
    row_count: Optional[int] = None
    created_at: Optional[str] = None
