"""
传导路径映射器

职责：
    - 结合知识图谱路径与油价预测变化，输出自然语言传导叙述
    - 增强行业冲击分析的可解释性

禁止：
    - 在此文件中做预测计算
    - 在此文件中修改图谱数据
"""

from app.knowledge_graph.graph_query import GraphQuery
from app.core.logger import get_logger

logger = get_logger(__name__)


class TransmissionMapper:
    """
    传导路径映射器。

    利用知识图谱的路径数据生成油价变化对各行业的传导叙述。
    """

    def __init__(self) -> None:
        """初始化，加载图谱查询器（单例）。"""
        self._graph = GraphQuery()
        self._alias_map = {
            "refinery": "chemical",
            "logistics": "shipping",
            "heavy_manufacturing": "manufacturing",
        }

    def build_transmission_narrative(
        self,
        industry_key: str,
        predicted_return: float,
    ) -> str:
        """
        构建油价变化通过知识图谱传导到指定行业的叙述。

        Args:
            industry_key: 行业标识符（aviation / shipping / chemical 等）。
            predicted_return: 预测油价收益率（正=上涨，负=下跌）。

        Returns:
            自然语言传导叙述字符串。
        """
        mapped_key = self._alias_map.get(industry_key, industry_key)
        path_labels = self._graph.get_path_labels(mapped_key)

        if not path_labels:
            return f"暂无 {industry_key} 的知识图谱传导路径数据。"

        arrow_path = " → ".join(path_labels)
        direction = "上涨" if predicted_return > 0 else "下跌"
        pct = abs(predicted_return * 100)

        # 判断最终节点类型（利好/利空）
        path_ids = self._graph.get_path(mapped_key)
        last_node = path_ids[-1] if path_ids else ""

        if len(path_ids) >= 2:
            weight = self._graph.get_edge_weight(path_ids[-2], last_node)
            impact_word = "正向提振" if weight > 0 else "负向压制"
        else:
            impact_word = "直接影响"

        narrative = (
            f"油价{direction} {pct:.2f}% 的传导路径：{arrow_path}。"
            f"最终对 {path_labels[-1]} 形成{impact_word}。"
        )

        logger.debug(f"传导叙述构建完成 industry={industry_key}")
        return narrative

    def enrich_industry_narratives(
        self,
        industries: list[str],
        predicted_return: float,
    ) -> dict[str, str]:
        """
        批量生成所有行业的传导叙述。

        Args:
            industries: 行业标识符列表。
            predicted_return: 预测油价收益率。

        Returns:
            {industry_key: 传导叙述} 字典。
        """
        return {
            industry: self.build_transmission_narrative(industry, predicted_return)
            for industry in industries
        }
