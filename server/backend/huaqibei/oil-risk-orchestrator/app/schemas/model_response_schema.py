"""
模型调用响应 Schema

职责：
    - 定义云端模型 API 返回数据结构
    - 所有字段均为 Optional，增强容错性

禁止：
    - 在此文件中写业务逻辑
"""

from pydantic import BaseModel, Field
from typing import Optional


class ShapValues(BaseModel):
    """SHAP 特征贡献值字典（特征名 → 贡献分数）。"""

    values: dict[str, float] = Field(
        default_factory=dict,
        description="各特征的 SHAP 贡献值",
    )
    base_value: float = Field(default=0.0, description="SHAP 基准值")


class MultiHorizonReturnPoint(BaseModel):
    """多周期收益率预测点（用于 1/3/7/14/30 天带状区间）。"""

    horizon: int = Field(..., description="预测周期（天）")
    predicted_return: float = Field(..., description="该周期预测收益率")
    lower_return: float = Field(..., description="该周期收益率下界")
    upper_return: float = Field(..., description="该周期收益率上界")


class ModelRawResponse(BaseModel):
    """
    云端模型原始返回格式。

    情况 A：模型返回完整 SHAP → shap_values 非空
    情况 B：模型仅返回预测值 → shap_values 为空，由本地解释层补充
    """

    median: float = Field(..., description="预测中位数收益率")
    upper: float = Field(..., description="预测上界（95% 置信）")
    lower: float = Field(..., description="预测下界（95% 置信）")
    confidence_score: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="模型置信度",
    )
    shap_values: Optional[ShapValues] = Field(
        None,
        description="SHAP 特征贡献（可选，模型未返回时为 None）",
    )
    forecast_horizon: int = Field(default=5, description="实际预测步数")
    model_version: Optional[str] = Field(None, description="模型版本号")
    multi_horizon_returns: list[MultiHorizonReturnPoint] = Field(
        default_factory=list,
        description="多周期收益率预测点（如 1/3/7/14/30 天）",
    )
