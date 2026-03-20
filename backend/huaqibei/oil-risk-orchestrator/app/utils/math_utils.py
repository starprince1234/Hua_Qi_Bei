"""
数学工具函数
"""

import math
from typing import Sequence


def clamp(value: float, min_val: float, max_val: float) -> float:
    """将值限制在 [min_val, max_val] 范围内。"""
    return max(min_val, min(max_val, value))


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """安全除法，分母为 0 时返回 default。"""
    if denominator == 0:
        return default
    return numerator / denominator


def rolling_std(values: Sequence[float], window: int) -> list[float]:
    """
    计算滚动标准差。

    Args:
        values: 数值序列。
        window: 窗口大小。

    Returns:
        与输入等长的标准差列表，窗口不足时为 0.0。
    """
    result: list[float] = []
    for i in range(len(values)):
        if i < window - 1:
            result.append(0.0)
        else:
            window_vals = list(values[i - window + 1 : i + 1])
            mean = sum(window_vals) / window
            variance = sum((v - mean) ** 2 for v in window_vals) / window
            result.append(math.sqrt(variance))
    return result


def pct_change(current: float, previous: float) -> float:
    """计算百分比变化率。"""
    return safe_divide(current - previous, previous)


def normalize_to_range(
    value: float, min_val: float, max_val: float
) -> float:
    """Min-max 归一化到 [0, 1]。"""
    span = max_val - min_val
    if span == 0:
        return 0.5
    return clamp((value - min_val) / span, 0.0, 1.0)
