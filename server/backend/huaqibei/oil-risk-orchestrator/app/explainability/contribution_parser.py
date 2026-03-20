"""
贡献解析器

职责：
    - 将 SHAP 值与因子字典结合，输出结构化贡献分析
    - 支持按类别汇总（宏观/技术/金融等）

禁止：
    - 在此文件中调用模型
    - 在此文件中生成最终报告文本
"""

from app.explainability.factor_dictionary import get_factor_info
from app.core.constants import FactorCategory
from app.core.logger import get_logger

logger = get_logger(__name__)


class ContributionParser:
    """
    贡献解析器。

    职责：
        - 将 {factor: shap_value} 字典解析为带元信息的贡献条目
        - 按因子类别聚合贡献
    """

    def parse(self, shap_values: dict[str, float]) -> list[dict]:
        """
        解析 SHAP 值字典为带元信息的贡献条目列表。

        Args:
            shap_values: {因子名: SHAP贡献值} 字典。

        Returns:
            包含因子名、中文名、类别、贡献值、方向的条目列表，
            按|贡献值|降序排列。
        """
        parsed: list[dict] = []

        for factor_name, shap_val in shap_values.items():
            info = get_factor_info(factor_name)
            parsed.append(
                {
                    "factor_name": factor_name,
                    "factor_name_cn": info["name_cn"],
                    "category": info["category"].value,
                    "definition": info["definition"],
                    "shap_value": round(shap_val, 6),
                    "direction": "positive" if shap_val > 0 else "negative",
                    "abs_value": abs(shap_val),
                }
            )

        parsed.sort(key=lambda x: x["abs_value"], reverse=True)

        logger.debug(f"贡献解析完成 factor_count={len(parsed)}")
        return parsed

    def aggregate_by_category(
        self, parsed_contributions: list[dict]
    ) -> dict[str, float]:
        """
        按因子类别汇总贡献值之和。

        Args:
            parsed_contributions: parse() 方法返回的条目列表。

        Returns:
            {类别: 贡献值之和} 字典。
        """
        category_sum: dict[str, float] = {}

        for item in parsed_contributions:
            cat = item["category"]
            category_sum[cat] = category_sum.get(cat, 0.0) + item["shap_value"]

        return category_sum
