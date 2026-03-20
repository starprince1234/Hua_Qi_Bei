"""
传导映射器

职责：
    - 将预测收益率与行业敏感度结合，生成量化传导影响
    - 确定各节点的影响方向与强度
"""

from typing import Any

from app.core.logger import get_logger
from app.utils.math_utils import clamp, normalize_to_range

logger = get_logger(__name__)

# 传导方向与预测收益率的映射规则
_DIRECTION_RULES: dict[str, dict[str, str]] = {
    "negative": {
        "up": "利空",
        "down": "利多",
    },
    "positive": {
        "up": "利多",
        "down": "利空",
    },
    "mixed": {
        "up": "中性",
        "down": "中性",
    },
}


class TransmissionMapper:
    """
    传导影响量化映射器。

    根据预测收益率与行业敏感度，计算各行业节点的影响强度与方向。
    """

    def map(
        self,
        paths: list[dict[str, Any]],
        predicted_return: float,
    ) -> list[dict[str, Any]]:
        """
        为传导路径计算每个节点的影响量化信息。

        Args:
            paths: GraphQuery.get_transmission_paths() 返回的路径列表。
            predicted_return: 预测收益率。

        Returns:
            包含量化影响信息的扩展路径列表。
        """
        price_direction = "up" if predicted_return >= 0 else "down"
        abs_return = abs(predicted_return)

        result: list[dict[str, Any]] = []
        for path in paths:
            sensitivity = float(path.get("sensitivity", 0.5))
            transmission_dir = str(path.get("transmission_direction", "mixed"))

            # 冲击强度 = 收益率幅度 × 行业敏感度，归一化到 [0, 1]
            raw_magnitude = abs_return * sensitivity
            impact_magnitude = clamp(
                normalize_to_range(raw_magnitude, 0.0, 0.15), 0.0, 1.0
            )

            direction_map = _DIRECTION_RULES.get(transmission_dir, _DIRECTION_RULES["mixed"])
            impact_direction = direction_map.get(price_direction, "中性")

            # 为每个节点分配衰减后的影响等级
            nodes = path.get("path_labels", [])
            node_impacts: list[dict[str, Any]] = []
            for idx, node in enumerate(nodes):
                decay = max(0.3, 1.0 - idx * 0.15)
                node_impacts.append(
                    {
                        "node": node,
                        "impact_score": round(impact_magnitude * decay, 4),
                        "impact_direction": impact_direction,
                        "depth": idx,
                    }
                )

            extended = dict(path)
            extended["impact_magnitude"] = round(impact_magnitude, 4)
            extended["impact_direction"] = impact_direction
            extended["node_impacts"] = node_impacts
            result.append(extended)

        logger.debug(f"TransmissionMapper: 处理 {len(paths)} 条路径，predicted_return={predicted_return:.4f}")
        return result
