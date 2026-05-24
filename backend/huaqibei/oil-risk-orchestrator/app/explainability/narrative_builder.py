"""
叙述构建器

职责：
    - 将结构化贡献数据转换为自然语言叙述段落
    - 生成可用于报告的中文解释文本

禁止：
    - 在此文件中做任何数值计算
    - 在此文件中调用外部 API
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


class NarrativeBuilder:
    """
    叙述构建器。

    将因子贡献解析结果转化为自然语言段落，
    主要供报告生成模块和解释层 API 使用。
    """

    def build_factor_narrative(
        self,
        parsed_contributions: list[dict],
        top_n: int = 5,
    ) -> str:
        """
        生成因子贡献叙述段落。

        Args:
            parsed_contributions: ContributionParser.parse() 返回的列表。
            top_n: 展示前 N 个因子。

        Returns:
            自然语言段落字符串。
        """
        if not parsed_contributions:
            return "当前无可用因子贡献数据。"

        top = parsed_contributions[:top_n]

        positive = [f for f in top if f["direction"] == "positive"]
        negative = [f for f in top if f["direction"] == "negative"]

        parts: list[str] = []

        if positive:
            pos_names = "、".join(f["factor_name_cn"] for f in positive[:3])
            parts.append(f"正向驱动因子包括：{pos_names}")

        if negative:
            neg_names = "、".join(f["factor_name_cn"] for f in negative[:3])
            parts.append(f"负向抑制因子包括：{neg_names}")

        narrative = "；".join(parts) + "。"

        logger.debug(f"因子叙述构建完成 chars={len(narrative)}")
        return narrative

    def build_category_narrative(
        self,
        category_sums: dict[str, float],
    ) -> str:
        """
        生成类别贡献叙述段落。

        Args:
            category_sums: ContributionParser.aggregate_by_category() 返回值。

        Returns:
            自然语言段落字符串。
        """
        if not category_sums:
            return "类别贡献数据暂不可用。"

        # 按绝对值降序排列
        sorted_cats = sorted(
            category_sums.items(), key=lambda x: abs(x[1]), reverse=True
        )

        category_cn_map = {
            "macro": "宏观因子",
            "supply": "供给因子",
            "demand": "需求因子",
            "geo": "地缘政治因子",
            "financial": "金融因子",
            "technical": "技术面因子",
        }

        descriptions: list[str] = []
        for cat, total in sorted_cats[:3]:
            cat_cn = category_cn_map.get(cat, cat)
            direction = "正贡献" if total > 0 else "负贡献"
            descriptions.append(f"{cat_cn}合计{direction} {total:+.4f}")

        return "因子类别贡献：" + "，".join(descriptions) + "。"
