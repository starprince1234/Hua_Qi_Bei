"""
报告数据模式定义
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .request_schema import Horizon


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"


class QuantilePrediction(BaseModel):
    """分位数预测结果"""

    q10: float = Field(..., description="10% 分位数预测回报率")
    q50: float = Field(..., description="50% 分位数（中位数）预测回报率")
    q90: float = Field(..., description="90% 分位数预测回报率")


class ShapContribution(BaseModel):
    """SHAP 特征贡献值"""

    feature: str = Field(..., description="特征名称")
    shap_value: float = Field(..., description="SHAP 贡献值（正负方向均有意义）")
    feature_value: float = Field(..., description="该特征的原始输入值")


class HorizonReport(BaseModel):
    """单一时间窗口预测报告"""

    horizon: Horizon
    prediction: QuantilePrediction
    risk_level: str = Field(..., description="风险等级: low / medium / high / extreme")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="归一化风险评分 [0, 1]")
    ai_insight: Optional[str] = Field(default=None, description="AI 生成的文字洞察")
    factor_reasons: List[str] = Field(default_factory=list, description="主要驱动因素说明")
    shap_contributions: Optional[List[ShapContribution]] = Field(default=None, description="SHAP 归因列表")


class PredictionReport(BaseModel):
    """完整预测报告"""

    report_id: str = Field(..., description="报告唯一标识符")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="报告生成时间（UTC）")
    upload_id: Optional[str] = Field(default=None, description="关联的数据上传标识符")
    horizons: List[HorizonReport] = Field(..., description="各时间窗口的预测结果")
    summary: Optional[str] = Field(default=None, description="综合摘要文字")
    metadata: Dict[str, object] = Field(default_factory=dict, description="附加元数据")
