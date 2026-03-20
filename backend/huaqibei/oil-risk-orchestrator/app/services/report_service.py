"""
报告生成服务

职责：
    - 编排预测结果、行业冲击、知识图谱、AI 解释为完整风险报告
    - 支持 JSON 与 Markdown 两种输出格式
"""

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.knowledge_graph.graph_query import GraphQuery
from app.schemas.industry_schema import IndustryImpactResult
from app.schemas.prediction_schema import PredictionResult
from app.schemas.report_schema import (
    AIIndustryInsight,
    AIKnowledgeGraphInsight,
    AIRiskInsight,
    KnowledgeGraphSection,
    RiskReport,
)

logger = get_logger(__name__)


class ReportService:
    """
    风险报告生成服务。
    """

    def __init__(self) -> None:
        self._graph = GraphQuery()

    async def build_report(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        factor_reasons: list[dict[str, Any]] | None = None,
        ai_risk_insight: AIRiskInsight | None = None,
        ai_industry_insight: AIIndustryInsight | None = None,
        ai_kg_insight: AIKnowledgeGraphInsight | None = None,
        node_levels: dict[str, dict[str, str]] | None = None,
        report_format: str = "json",
    ) -> RiskReport:
        """
        构建完整风险报告。

        Args:
            prediction: 预测结果。
            industry_impact: 行业冲击分析结果。
            factor_reasons: 因子驱动原因列表。
            ai_risk_insight: AI 风险详情（可选）。
            ai_industry_insight: AI 行业详情（可选）。
            ai_kg_insight: AI 知识图谱详情（可选）。
            node_levels: 节点影响等级字典（可选）。
            report_format: 报告格式（json/markdown）。

        Returns:
            RiskReport 完整报告。
        """
        final_return = (
            prediction.prediction_path[-1].predicted_return
            if prediction.prediction_path
            else 0.0
        )

        # 获取知识图谱传导路径
        kg_paths = self._graph.get_transmission_paths(
            top_n=5,
            predicted_return=final_return,
        )

        kg_section = KnowledgeGraphSection(
            paths=kg_paths,
            node_levels=node_levels or {},
            ai_insight=ai_kg_insight,
        )

        report = RiskReport(
            report_id=str(uuid.uuid4()),
            prediction=prediction,
            industry_impact=industry_impact,
            knowledge_graph=kg_section,
            factor_reasons=factor_reasons or [],
            ai_risk_insight=ai_risk_insight,
            ai_industry_insight=ai_industry_insight,
            created_at=datetime.now(timezone.utc).isoformat(),
            report_format=report_format,
        )

        logger.info(f"ReportService: 报告生成完成 report_id={report.report_id}")
        return report

    def to_markdown(self, report: RiskReport) -> str:
        """
        将风险报告转换为 Markdown 格式文本。

        Args:
            report: RiskReport 对象。

        Returns:
            Markdown 字符串。
        """
        pred = report.prediction
        risk = pred.risk_assessment
        lines: list[str] = [
            f"# 油价风险报告",
            f"",
            f"**报告 ID**: {report.report_id}",
            f"**生成时间**: {report.created_at}",
            f"",
            f"## 预测摘要",
            f"",
            f"- 当前价格: **${pred.current_price:.2f}**",
            f"- 预测步数: **{pred.forecast_horizon} 天**",
            f"- 趋势方向: **{risk.trend_display}**",
            f"- 风险等级: **{risk.level.value}**",
            f"- 模型置信度: **{risk.confidence_score * 100:.1f}%**",
            f"",
        ]

        if pred.prediction_path:
            final = pred.prediction_path[-1]
            lines += [
                f"## 预测终点",
                f"",
                f"- 预测价格: **${final.predicted_price:.2f}**",
                f"- 预测收益率: **{final.predicted_return * 100:+.2f}%**",
                f"",
            ]

        if report.ai_risk_insight:
            lines += [
                f"## AI 风险详情",
                f"",
                report.ai_risk_insight.detail,
                f"",
            ]

        if report.industry_impact.impacts:
            lines += [f"## 行业冲击分析", f"", report.industry_impact.summary, f""]
            for item in report.industry_impact.impacts:
                lines.append(
                    f"- **{item.industry}**: {item.impact_direction.value}，"
                    f"强度 {item.impact_magnitude * 100:.1f}%"
                )
            lines.append("")

        if report.factor_reasons:
            lines += [f"## 关键因子解释", f""]
            for fr in report.factor_reasons[:5]:
                lines.append(f"- **{fr['feature']}**: {fr['reason']}")
            lines.append("")

        return "\n".join(lines)
