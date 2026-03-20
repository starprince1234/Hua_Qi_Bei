"""
预测结果 Schema
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class TrendDirection(str, Enum):
    UP = "上涨"
    DOWN = "下跌"
    FLAT = "震荡"


class PredictionPathPoint(BaseModel):
    """单步预测路径点。"""

    day: int = Field(..., description="第几天")
    predicted_price: float = Field(..., description="预测价格（美元/桶）")
    predicted_return: float = Field(..., description="预测收益率")
    upper_price: Optional[float] = Field(None)
    lower_price: Optional[float] = Field(None)


class RiskAssessment(BaseModel):
    """风险评估结果。"""

    level: RiskLevel = Field(..., description="风险等级")
    trend_display: str = Field(..., description="趋势展示文字")
    max_return_change: float = Field(..., description="最大收益变化幅度")
    confidence_score: float = Field(..., description="模型置信度")
    volatility: float = Field(0.0, description="预测路径波动率")


class PredictionResult(BaseModel):
    """完整预测结果。"""

    prediction_id: str = Field(..., description="预测唯一 ID")
    current_price: float = Field(..., description="当前价格")
    forecast_horizon: int = Field(..., description="预测步数")
    prediction_path: list[PredictionPathPoint] = Field(
        default_factory=list, description="逐步预测路径"
    )
    risk_assessment: RiskAssessment
    shap_top_features: list[dict] = Field(
        default_factory=list, description="Top SHAP 特征列表"
    )
    model_version: Optional[str] = None
    created_at: Optional[str] = None
