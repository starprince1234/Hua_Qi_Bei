"""
数据上传服务
"""
from __future__ import annotations

import io
import uuid
from typing import List

import pandas as pd
from fastapi import UploadFile

from ..schemas.upload_schema import UploadResponse, UploadValidationResult

# 必须存在的特征列集合（最小集）
REQUIRED_FEATURE_COLUMNS: List[str] = []


def parse_upload(file: UploadFile) -> tuple[str, pd.DataFrame]:
    """解析上传的 Excel 或 CSV 文件，返回 (upload_id, dataframe)。"""
    content = file.file.read()
    filename = file.filename or ""

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content))
    else:
        df = pd.read_excel(io.BytesIO(content))

    upload_id = str(uuid.uuid4())
    return upload_id, df


def build_upload_response(upload_id: str, filename: str, df: pd.DataFrame) -> UploadResponse:
    """根据解析结果构建上传响应对象。"""
    warnings: List[str] = []

    null_cols = [col for col in df.columns if df[col].isnull().any()]
    if null_cols:
        warnings.append(f"以下列存在空值: {', '.join(null_cols)}")

    return UploadResponse(
        upload_id=upload_id,
        filename=filename,
        row_count=len(df),
        column_count=len(df.columns),
        columns=list(df.columns),
        warnings=warnings,
    )


def validate_upload(upload_id: str, df: pd.DataFrame) -> UploadValidationResult:
    """验证上传数据是否包含必要特征列。"""
    existing = set(df.columns)
    required = set(REQUIRED_FEATURE_COLUMNS)

    missing = sorted(required - existing)
    extra = sorted(existing - required)

    valid = len(missing) == 0
    error_message = f"缺失必要特征列: {missing}" if not valid else None

    return UploadValidationResult(
        upload_id=upload_id,
        valid=valid,
        missing_features=missing,
        extra_columns=extra,
        error_message=error_message,
    )
