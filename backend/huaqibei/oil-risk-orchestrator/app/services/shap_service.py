"""
SHAP 解释服务

职责：
    - 将模型返回的 SHAP 值转化为有序贡献列表
    - 生成 SHAP 叙事文本
"""

from typing import Any

from app.core.logger import get_logger
from app.explainability.contribution_parser import ContributionParser
from app.explainability.narrative_builder import NarrativeBuilder
from app.schemas.model_response_schema import ShapValues

logger = get_logger(__name__)


class ShapService:
    """
    SHAP 解释服务。

    封装 SHAP 值的解析与叙事生成流程。
    """

    def __init__(self) -> None:
        self._parser = ContributionParser()
        self._narrator = NarrativeBuilder()

    def process(
        self,
        shap_values: ShapValues | None,
        predicted_return: float,
        forecast_horizon: int,
    ) -> tuple[list[dict[str, Any]], str]:
        """
        处理 SHAP 值，返回结构化贡献列表和叙事文本。

        Args:
            shap_values: 模型返回的 ShapValues 对象（可为 None）。
            predicted_return: 预测收益率。
            forecast_horizon: 预测步数。

        Returns:
            (contributions, narrative) 元组。
        """
        if shap_values is None or not shap_values.values:
            return [], "暂无 SHAP 解释数据。"

        contributions = self._parser.parse(
            shap_values.values,
            base_value=shap_values.base_value,
        )
        narrative = self._narrator.build_shap_narrative(
            contributions=contributions,
            predicted_return=predicted_return,
            forecast_horizon=forecast_horizon,
        )

        logger.debug(f"ShapService: 处理 {len(shap_values.values)} 个特征，返回 {len(contributions)} 个贡献项")
        return contributions, narrative
