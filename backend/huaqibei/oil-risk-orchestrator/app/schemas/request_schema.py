"""
请求体 Schema
"""

from pydantic import BaseModel, Field
from typing import Optional


class OilDataRecord(BaseModel):
    """单条油价数据记录。"""

    date: str = Field(..., description="日期，格式 YYYY-MM-DD")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    close: Optional[float] = Field(None, description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")


class PredictRequest(BaseModel):
    """预测接口请求体。"""

    data: list[OilDataRecord] = Field(..., description="历史油价时序数据")
    forecast_horizon: int = Field(7, ge=1, le=30, description="预测步数（天）")
    include_shap: bool = Field(True, description="是否返回 SHAP 解释")
    include_report: bool = Field(False, description="是否同时生成报告")
    mock_mode: bool = Field(False, description="是否使用 Mock 模型（测试用）")


class ReportRequest(BaseModel):
    """报告生成接口请求体。"""

    prediction_id: Optional[str] = Field(None, description="预测结果 ID（用于缓存复用）")
    data: Optional[list[OilDataRecord]] = Field(None, description="原始数据（无缓存时必填）")
    forecast_horizon: int = Field(7, ge=1, le=30, description="预测步数")
    report_format: str = Field("json", description="报告格式：json / markdown")
    mock_mode: bool = Field(False, description="是否使用 Mock 模型")
