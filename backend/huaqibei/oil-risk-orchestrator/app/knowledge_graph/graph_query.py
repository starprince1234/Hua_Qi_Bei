"""
知识图谱查询模块

职责：
    - 加载 graph_data.json 并提供查询接口
    - 支持节点查找、路径查找、边权查询

禁止：
    - 在此文件中做业务分析
    - 在此文件中修改图谱数据
"""

import json
from pathlib import Path
from typing import Optional
from app.core.logger import get_logger

logger = get_logger(__name__)

# 图谱数据相对路径
_GRAPH_DATA_PATH = Path(__file__).parent / "graph_data.json"


class GraphQuery:
    """
    知识图谱查询器。

    单例加载图谱数据，提供节点/边/路径查询接口。
    """

    _instance: Optional["GraphQuery"] = None
    _graph_data: dict = {}

    def __new__(cls) -> "GraphQuery":
        """单例模式：图谱数据只加载一次。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_graph()
        return cls._instance

    def _load_graph(self) -> None:
        """加载图谱 JSON 文件。"""
        try:
            with open(_GRAPH_DATA_PATH, encoding="utf-8") as f:
                self._graph_data = json.load(f)
            node_count = len(self._graph_data.get("nodes", []))
            edge_count = len(self._graph_data.get("edges", []))
            logger.info(f"知识图谱加载完成 nodes={node_count} edges={edge_count}")
        except FileNotFoundError:
            logger.error(f"知识图谱文件不存在: {_GRAPH_DATA_PATH}")
            self._graph_data = {"nodes": [], "edges": [], "paths": {}}
        except json.JSONDecodeError as e:
            logger.error(f"知识图谱 JSON 解析失败: {e}")
            self._graph_data = {"nodes": [], "edges": [], "paths": {}}

    def get_path(self, industry_key: str) -> list[str]:
        """
        获取指定行业的传导路径节点 ID 列表。

        Args:
            industry_key: 行业标识符（与 graph_data.json paths 字段一致）。

        Returns:
            节点 ID 列表，若未找到则返回空列表。
        """
        return self._graph_data.get("paths", {}).get(industry_key, [])

    def get_node_label(self, node_id: str) -> str:
        """
        获取节点中文标签。

        Args:
            node_id: 节点 ID。

        Returns:
            节点标签，未找到返回 node_id 本身。
        """
        for node in self._graph_data.get("nodes", []):
            if node["id"] == node_id:
                return node["label"]
        return node_id

    def get_edge_weight(self, from_id: str, to_id: str) -> float:
        """
        获取两节点间边的权重。

        Args:
            from_id: 起始节点 ID。
            to_id: 目标节点 ID。

        Returns:
            边权重（正值为正向传导，负值为反向）。未找到返回 0.0。
        """
        for edge in self._graph_data.get("edges", []):
            if edge["from"] == from_id and edge["to"] == to_id:
                return float(edge["weight"])
        return 0.0

    def get_path_labels(self, industry_key: str) -> list[str]:
        """
        获取传导路径的中文标签列表（用于展示）。

        Args:
            industry_key: 行业标识符。

        Returns:
            中文标签列表。
        """
        path = self.get_path(industry_key)
        return [self.get_node_label(node_id) for node_id in path]
