"""
报告 Schema

包含：
  - 完整风险报告
  - AI 增强解释块
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field

from app.schemas.industry_schema import IndustryImpactResult
from app.schemas.prediction_schema import PredictionResult


class AIRiskInsight(BaseModel):
    """AI 生成的风险详情。"""

    risk_level: str = Field(..., description="AI 判定的风险等级 LOW/MEDIUM/HIGH")
    detail: str = Field(..., description="风险详情文本")
    model_id: str = Field("", description="使用的 LLM 模型 ID")


class AIIndustryInsight(BaseModel):
    """AI 生成的行业冲击详情。"""

    detail: str = Field(..., description="行业冲击详情文本")
    model_id: str = Field("", description="使用的 LLM 模型 ID")


class AIKnowledgeGraphInsight(BaseModel):
    """AI 生成的知识图谱详情。"""

    detail: str = Field(..., description="知识图谱传导路径详情文本")
    model_id: str = Field("", description="使用的 LLM 模型 ID")


class KnowledgeGraphSection(BaseModel):
    """报告中的知识图谱板块。"""

    paths: list[dict[str, Any]] = Field(default_factory=list, description="传导路径列表")
    node_levels: dict[str, dict[str, str]] = Field(
        default_factory=dict, description="节点影响等级 {行业: {节点: 等级}}"
    )
    ai_insight: Optional[AIKnowledgeGraphInsight] = None


class RiskReport(BaseModel):
    """完整风险报告。"""

    report_id: str = Field(..., description="报告唯一 ID")
    prediction: PredictionResult
    industry_impact: IndustryImpactResult
    knowledge_graph: KnowledgeGraphSection
    factor_reasons: list[dict[str, Any]] = Field(
        default_factory=list, description="关键因子驱动原因"
    )
    ai_risk_insight: Optional[AIRiskInsight] = None
    ai_industry_insight: Optional[AIIndustryInsight] = None
    created_at: Optional[str] = None
    report_format: str = Field("json", description="报告格式")
