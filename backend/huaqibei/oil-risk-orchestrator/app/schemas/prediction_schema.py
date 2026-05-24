"""
预测结果 Schema

职责：
    - 定义经后处理的预测结果数据结构
    - 包含路径还原、风险分级结果

禁止：
    - 在此文件中写计算逻辑
"""

from pydantic import BaseModel, Field
from typing import Optional
from app.core.constants import RiskLevel, TrendDirection


class PredictionPoint(BaseModel):
    """单步预测结果。"""

    step: int = Field(..., description="预测步数（第几天）")
    predicted_return: float = Field(..., description="预测收益率")
    predicted_price: float = Field(..., description="还原后的预测价格 (USD)")
    upper_price: float = Field(..., description="置信上界价格 (USD)")
    lower_price: float = Field(..., description="置信下界价格 (USD)")


class RiskAssessment(BaseModel):
    """风险评估结果。"""

    level: RiskLevel = Field(..., description="风险等级")
    level_display: str = Field(..., description="风险等级中文名")
    max_return_change: float = Field(..., description="最大预测收益率变化")
    confidence_score: float = Field(..., description="模型置信度")
    trend: TrendDirection = Field(..., description="趋势方向")
    trend_display: str = Field(..., description="趋势方向中文名")
    signal: str = Field(..., description="风险信号摘要文本")


class PredictionResult(BaseModel):
    """完整预测结果（含路径 + 风险评估）。"""

    current_price: float = Field(..., description="当前基准价格 (USD)")
    forecast_horizon: int = Field(..., description="预测步数")
    prediction_path: list[PredictionPoint] = Field(..., description="逐步预测路径")
    risk_assessment: RiskAssessment = Field(..., description="风险评估结果")
    model_version: Optional[str] = Field(None, description="模型版本")
