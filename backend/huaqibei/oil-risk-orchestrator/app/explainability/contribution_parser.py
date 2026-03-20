"""
SHAP 贡献解析器

职责：
    - 将模型返回的 SHAP 字典转换为有序的贡献列表
    - 过滤噪声特征，返回 Top-N 显著贡献因子
"""

from typing import Any

from app.core.constants import MAX_SHAP_FEATURES_DISPLAY
from app.core.logger import get_logger

logger = get_logger(__name__)


class ContributionParser:
    """
    SHAP 贡献值解析器。
    """

    def __init__(self, top_n: int = MAX_SHAP_FEATURES_DISPLAY) -> None:
        self._top_n = top_n

    def parse(
        self,
        shap_values: dict[str, float],
        base_value: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        解析 SHAP 值字典，返回有序贡献列表。

        Args:
            shap_values: {特征名: SHAP 值} 字典。
            base_value: SHAP 基准值（模型期望输出）。

        Returns:
            [{"feature": str, "shap_value": float, "direction": "positive"|"negative", "rank": int}, ...]
        """
        if not shap_values:
            return []

        sorted_items = sorted(
            shap_values.items(),
            key=lambda kv: abs(kv[1]),
            reverse=True,
        )

        result: list[dict[str, Any]] = []
        for rank, (feat, val) in enumerate(sorted_items[: self._top_n], start=1):
            result.append(
                {
                    "feature": feat,
                    "shap_value": round(val, 6),
                    "direction": "positive" if val >= 0 else "negative",
                    "rank": rank,
                    "base_value": round(base_value, 6),
                }
            )

        logger.debug(f"ContributionParser: 解析 {len(shap_values)} 个特征，返回 Top-{len(result)}")
        return result
