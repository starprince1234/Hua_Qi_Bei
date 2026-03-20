"""
叙事文本构建器

职责：
    - 将 SHAP 贡献列表转化为自然语言叙事
    - 结合因子字典提供中文可读的因子解释
"""

from typing import Any

from app.explainability.factor_dictionary import get_display_name, get_factor_group
from app.core.logger import get_logger

logger = get_logger(__name__)


class NarrativeBuilder:
    """
    叙事文本生成器。

    将量化解释（SHAP 值）转化为人类可读的自然语言摘要。
    """

    def build_shap_narrative(
        self,
        contributions: list[dict[str, Any]],
        predicted_return: float,
        forecast_horizon: int,
    ) -> str:
        """
        生成 SHAP 贡献叙事摘要。

        Args:
            contributions: ContributionParser 输出的贡献列表。
            predicted_return: 模型预测的收益率。
            forecast_horizon: 预测步数（天）。

        Returns:
            自然语言叙事字符串。
        """
        if not contributions:
            return f"模型预测未来 {forecast_horizon} 天油价变动方向不明确，暂无关键因子解释。"

        direction = "上涨" if predicted_return >= 0 else "下跌"
        pct = abs(predicted_return) * 100

        top_positive = [c for c in contributions if c["direction"] == "positive"][:3]
        top_negative = [c for c in contributions if c["direction"] == "negative"][:3]

        lines: list[str] = [
            f"模型预测未来 {forecast_horizon} 天内油价预期{direction}约 {pct:.2f}%。"
        ]

        if top_positive:
            names = "、".join(get_display_name(c["feature"]) for c in top_positive)
            lines.append(f"推动上行的主要因子：{names}，对预测结果产生正向贡献。")

        if top_negative:
            names = "、".join(get_display_name(c["feature"]) for c in top_negative)
            lines.append(f"施加下行压力的主要因子：{names}，对预测结果产生负向贡献。")

        # 分组汇总
        group_counts: dict[str, int] = {}
        for c in contributions:
            g = get_factor_group(c["feature"])
            group_counts[g] = group_counts.get(g, 0) + 1

        if group_counts:
            group_summary = "；".join(f"{g}类因子 {n} 个" for g, n in group_counts.items())
            lines.append(f"本次预测共涉及 {len(contributions)} 个特征，分布为：{group_summary}。")

        return "\n".join(lines)
