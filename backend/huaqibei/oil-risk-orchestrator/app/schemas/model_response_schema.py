"""
模型原始响应 Schema
"""

from pydantic import BaseModel, Field
from typing import Optional


class ShapValues(BaseModel):
    """SHAP 值容器。"""

    values: dict[str, float] = Field(default_factory=dict, description="特征 -> SHAP 值")
    base_value: float = Field(0.0, description="SHAP 基准值（期望输出）")


class MultiHorizonReturnPoint(BaseModel):
    """多步预测中单步收益点。"""

    horizon: int = Field(..., description="预测步数（天）")
    predicted_return: float = Field(..., description="预测收益率")
    upper: Optional[float] = Field(None, description="上界")
    lower: Optional[float] = Field(None, description="下界")


class ModelRawResponse(BaseModel):
    """模型服务返回的原始结构化响应。"""

    median: float = Field(..., description="预测收益率中位数")
    upper: float = Field(..., description="置信区间上界")
    lower: float = Field(..., description="置信区间下界")
    confidence_score: float = Field(..., description="模型置信度 0-1")
    shap_values: Optional[ShapValues] = Field(None, description="SHAP 解释值")
    forecast_horizon: int = Field(..., description="预测步数")
    model_version: Optional[str] = Field(None, description="模型版本")
    multi_horizon_returns: list[MultiHorizonReturnPoint] = Field(
        default_factory=list, description="多步预测序列"
    )
