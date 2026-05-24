"""
行业冲击 Schema

职责：
    - 定义行业油价冲击分析结果结构
"""

from pydantic import BaseModel, Field
from app.core.constants import IndustrySector, ImpactDirection


class IndustryImpact(BaseModel):
    """单个行业的油价冲击分析结果。"""

    industry: str = Field(..., description="行业标识符")
    industry_name_cn: str = Field(..., description="行业中文名称")
    impact_direction: ImpactDirection = Field(..., description="冲击方向：利好/利空/中性")
    impact_magnitude: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="冲击强度 0~1",
    )
    transmission_path: list[str] = Field(
        default_factory=list,
        description="传导路径描述（知识图谱节点链）",
    )
    key_indicators: list[str] = Field(
        default_factory=list,
        description="受影响的关键指标",
    )
    narrative: str = Field(default="", description="冲击分析自然语言描述")


class IndustryImpactResult(BaseModel):
    """行业冲击全量分析结果。"""

    predicted_return_median: float = Field(..., description="预测收益率中位数")
    impacts: list[IndustryImpact] = Field(..., description="各行业冲击详情")
    high_alert_industries: list[str] = Field(
        default_factory=list,
        description="高度预警的行业列表",
    )
