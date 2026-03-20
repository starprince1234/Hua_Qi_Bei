"""
请求数据模式定义
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class Horizon(str, Enum):
    ONE_DAY = "1D"
    THREE_DAY = "3D"
    SEVEN_DAY = "7D"
    FOURTEEN_DAY = "14D"
    THIRTY_DAY = "30D"


class PredictRequest(BaseModel):
    """油价风险预测请求"""

    horizon: Horizon = Field(..., description="预测时间窗口")
    features: Dict[str, float] = Field(..., description="特征名称到数值的映射")
    include_shap: bool = Field(default=False, description="是否返回 SHAP 归因值")
    request_id: Optional[str] = Field(default=None, description="请求唯一标识符")


class BatchPredictRequest(BaseModel):
    """批量预测请求"""

    horizons: List[Horizon] = Field(default_factory=list, description="预测时间窗口列表")
    features: Dict[str, float] = Field(..., description="特征名称到数值的映射")
    include_shap: bool = Field(default=False, description="是否返回 SHAP 归因值")
    request_id: Optional[str] = Field(default=None, description="请求唯一标识符")
