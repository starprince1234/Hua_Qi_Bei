"""
行业冲击分析服务

职责：
    - 结合预测结果与知识图谱，计算各行业受油价变动的冲击程度
    - 生成行业冲击报告
"""

from typing import Any

from app.core.logger import get_logger
from app.knowledge_graph.graph_query import GraphQuery
from app.knowledge_graph.transmission_mapper import TransmissionMapper
from app.schemas.industry_schema import (
    ImpactDirection,
    IndustryImpactItem,
    IndustryImpactResult,
)
from app.schemas.prediction_schema import PredictionResult

logger = get_logger(__name__)


class IndustryService:
    """
    行业冲击分析服务。
    """

    def __init__(self) -> None:
        self._graph = GraphQuery()
        self._mapper = TransmissionMapper()

    def analyze(
        self,
        prediction: PredictionResult,
        top_n: int = 5,
    ) -> IndustryImpactResult:
        """
        分析各行业受油价预测结果的冲击。

        Args:
            prediction: 预测结果。
            top_n: 返回的最大行业数。

        Returns:
            IndustryImpactResult 行业冲击分析结果。
        """
        final_return = (
            prediction.prediction_path[-1].predicted_return
            if prediction.prediction_path
            else prediction.risk_assessment.max_return_change
        )

        paths = self._graph.get_transmission_paths(
            top_n=top_n,
            predicted_return=final_return,
        )
        mapped = self._mapper.map(paths=paths, predicted_return=final_return)

        impacts: list[IndustryImpactItem] = []
        for item in mapped:
            direction_str = item.get("impact_direction", "中性")
            if direction_str == "利多":
                direction = ImpactDirection.POSITIVE
            elif direction_str == "利空":
                direction = ImpactDirection.NEGATIVE
            else:
                direction = ImpactDirection.NEUTRAL

            narrative = self._build_narrative(
                industry=item["industry"],
                magnitude=item["impact_magnitude"],
                direction=direction_str,
                predicted_return=final_return,
            )

            impacts.append(
                IndustryImpactItem(
                    industry=item["industry"],
                    impact_magnitude=item["impact_magnitude"],
                    impact_direction=direction,
                    narrative=narrative,
                    sensitivity_score=item.get("sensitivity", 0.5),
                )
            )

        summary = self._build_summary(impacts=impacts, predicted_return=final_return)

        logger.debug(f"IndustryService: 分析 {len(impacts)} 个行业冲击")
        return IndustryImpactResult(impacts=impacts, summary=summary)

    def _build_narrative(
        self,
        industry: str,
        magnitude: float,
        direction: str,
        predicted_return: float,
    ) -> str:
        pct_return = abs(predicted_return) * 100
        pct_impact = magnitude * 100
        trend = "上涨" if predicted_return >= 0 else "下跌"
        return (
            f"油价预期{trend}约 {pct_return:.2f}%，传导至{industry}行业，"
            f"预估冲击强度约 {pct_impact:.1f}%（{direction}）。"
        )

    def _build_summary(
        self,
        impacts: list[IndustryImpactItem],
        predicted_return: float,
    ) -> str:
        if not impacts:
            return "暂无行业冲击数据。"
        most_affected = max(impacts, key=lambda x: x.impact_magnitude)
        trend = "上涨" if predicted_return >= 0 else "下跌"
        return (
            f"油价预期{trend}，受影响最大的行业为{most_affected.industry}，"
            f"冲击强度约 {most_affected.impact_magnitude * 100:.1f}%"
            f"（{most_affected.impact_direction.value}）。"
        )
