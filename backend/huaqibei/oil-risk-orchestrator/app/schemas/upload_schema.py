"""
上传数据模式定义
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    """文件上传响应"""

    upload_id: str = Field(..., description="上传任务唯一标识符")
    filename: str = Field(..., description="原始文件名")
    row_count: int = Field(..., description="解析到的数据行数")
    column_count: int = Field(..., description="解析到的数据列数")
    columns: List[str] = Field(..., description="列名列表")
    warnings: List[str] = Field(default_factory=list, description="数据质量警告")


class UploadValidationResult(BaseModel):
    """上传数据验证结果"""

    upload_id: str = Field(..., description="对应的上传任务标识符")
    valid: bool = Field(..., description="数据是否通过验证")
    missing_features: List[str] = Field(default_factory=list, description="缺失的必要特征列")
    extra_columns: List[str] = Field(default_factory=list, description="上传文件中多余的列")
    error_message: Optional[str] = Field(default=None, description="验证失败原因（若有）")
