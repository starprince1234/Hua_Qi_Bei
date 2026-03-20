"""
行业冲击 Schema
"""

from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class ImpactDirection(str, Enum):
    POSITIVE = "利多"
    NEGATIVE = "利空"
    NEUTRAL = "中性"


class IndustryImpactItem(BaseModel):
    """单个行业冲击条目。"""

    industry: str = Field(..., description="行业名称")
    impact_magnitude: float = Field(..., description="冲击强度（0-1）")
    impact_direction: ImpactDirection = Field(..., description="冲击方向")
    narrative: str = Field("", description="冲击叙述")
    sensitivity_score: float = Field(0.5, description="行业敏感度评分")


class IndustryImpactResult(BaseModel):
    """行业冲击分析结果。"""

    impacts: list[IndustryImpactItem] = Field(
        default_factory=list, description="各行业冲击列表"
    )
    summary: str = Field("", description="综合摘要")
