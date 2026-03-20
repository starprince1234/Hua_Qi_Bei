from __future__ import annotations

from datetime import datetime, timezone

from app.schemas.report_schema import ReportResponse, ReportSection
from app.core.logger import get_logger

logger = get_logger(__name__)

_STYLE_TITLES = {
    "banking": "油价风险智能分析报告（银行版）",
    "general": "油价风险智能分析报告",
}


async def generate_report(file_id: str, style: str = "general") -> ReportResponse | None:
    """
    Build a structured report for *file_id*.
    In production this would fetch a cached PredictionResponse; here we build a realistic placeholder.
    """
    now = datetime.now(timezone.utc).isoformat()
    title = _STYLE_TITLES.get(style, _STYLE_TITLES["general"])

    summary = ReportSection(
        title="执行摘要",
        content=(
            "根据最新上传数据，油价预测模型显示近期国际原油价格面临中等波动风险。"
            "模型综合分析地缘政治、OPEC产量决策、全球需求等核心驱动因素，"
            "建议相关企业提前做好燃油套期保值安排。"
        ),
        charts=[{"type": "line", "title": "价格预测曲线", "data_key": "predictions"}],
    )

    detail = ReportSection(
        title="详细分析",
        content=(
            "1. 供应面：OPEC+减产协议延续，中东地区地缘紧张局势为油价提供支撑。\n"
            "2. 需求面：中国经济复苏加速，航空及运输业燃油需求回升。\n"
            "3. 金融面：美元走弱及通胀预期为大宗商品提供上行动能。\n"
            "4. 风险因素：全球经济放缓风险及非OPEC供应增量可能对油价形成压制。"
        ),
        charts=[
            {"type": "bar", "title": "因素贡献度", "data_key": "factor_contributions"},
            {"type": "area", "title": "分位数预测带", "data_key": "quantiles"},
        ],
    )

    risk_section = ReportSection(
        title="风险指标",
        content="VaR(95%)、CVaR(95%) 及波动率指标详见附图。",
        charts=[{"type": "gauge", "title": "风险等级", "data_key": "risk_level"}],
    )

    industry_section = ReportSection(
        title="行业影响分析",
        content="航空、航运、化工行业成本传导路径及影响评估。",
        charts=[{"type": "radar", "title": "行业影响雷达图", "data_key": "industry_impacts"}],
    )

    return ReportResponse(
        file_id=file_id,
        style=style,
        title=title,
        generated_at=now,
        summary=summary,
        detail=detail,
        risk_section=risk_section,
        industry_section=industry_section,
    )
