"""
知识图谱查询

职责：
    - 从 graph_data.json 加载知识图谱
    - 提供路径查询、行业查询等接口
    - 返回标准化的传导路径数据
"""

import json
import os
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

_GRAPH_DATA_PATH = os.path.join(os.path.dirname(__file__), "graph_data.json")


def _load_graph_data() -> dict[str, Any]:
    """加载知识图谱 JSON 数据。"""
    try:
        with open(_GRAPH_DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"知识图谱数据加载失败: {e}，返回空图谱")
        return {"industries": [], "relationships": [], "meta": {}}


class GraphQuery:
    """
    知识图谱查询接口。

    提供行业路径查询、节点查询等功能。
    """

    def __init__(self) -> None:
        self._data = _load_graph_data()
        self._industries: list[dict[str, Any]] = self._data.get("industries", [])
        self._relationships: list[dict[str, Any]] = self._data.get("relationships", [])

    def get_all_industries(self) -> list[str]:
        """返回所有行业名称列表。"""
        return [ind["name"] for ind in self._industries]

    def get_transmission_paths(
        self,
        top_n: int = 5,
        predicted_return: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        获取传导路径列表（按行业敏感度排序）。

        Args:
            top_n: 返回的最大行业数量。
            predicted_return: 预测收益率（用于过滤方向）。

        Returns:
            传导路径列表，每条包含 industry / path_labels / sensitivity / direction。
        """
        sorted_industries = sorted(
            self._industries,
            key=lambda x: x.get("sensitivity", 0.0),
            reverse=True,
        )

        result: list[dict[str, Any]] = []
        for ind in sorted_industries[:top_n]:
            nodes = ind.get("nodes", [])
            if not nodes:
                continue
            direction = ind.get("transmission_direction", "mixed")
            result.append(
                {
                    "industry": ind["name"],
                    "path_labels": nodes,
                    "sensitivity": ind.get("sensitivity", 0.5),
                    "transmission_direction": direction,
                    "path_length": len(nodes),
                }
            )

        logger.debug(f"GraphQuery: 返回 {len(result)} 条传导路径")
        return result

    def get_industry_detail(self, industry_name: str) -> dict[str, Any] | None:
        """
        按名称查询行业详情。

        Args:
            industry_name: 行业名称。

        Returns:
            行业数据字典，未找到时返回 None。
        """
        for ind in self._industries:
            if ind["name"] == industry_name:
                return dict(ind)
        return None

    def get_related_relationships(self, node: str) -> list[dict[str, Any]]:
        """
        查询与指定节点相关的所有关系。

        Args:
            node: 节点名称。

        Returns:
            相关关系列表。
        """
        return [
            r for r in self._relationships
            if r.get("source") == node or r.get("target") == node
        ]
