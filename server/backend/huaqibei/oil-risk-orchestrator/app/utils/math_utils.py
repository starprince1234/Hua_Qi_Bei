"""
数学工具函数

职责：
    - 提供金融计算辅助函数
    - 收益率计算、标准化、分位数等

禁止：
    - 在此文件中写业务逻辑
    - 在此文件中写模型调用
"""

import math
from typing import Union


def compute_log_return(price_series: list[float]) -> list[float]:
    """
    计算对数收益率序列。

    Args:
        price_series: 价格序列（时间升序）。

    Returns:
        对数收益率序列（长度 = len(price_series) - 1）。

    Raises:
        ValueError: 价格序列过短或含非正值。
    """
    if len(price_series) < 2:
        raise ValueError("价格序列至少需要 2 个元素")
    if any(p <= 0 for p in price_series):
        raise ValueError("价格序列不能含非正值")

    return [
        math.log(price_series[i] / price_series[i - 1])
        for i in range(1, len(price_series))
    ]


def compute_simple_return(price_series: list[float]) -> list[float]:
    """
    计算简单收益率序列。

    Args:
        price_series: 价格序列（时间升序）。

    Returns:
        简单收益率序列。
    """
    if len(price_series) < 2:
        raise ValueError("价格序列至少需要 2 个元素")

    return [
        (price_series[i] - price_series[i - 1]) / price_series[i - 1]
        for i in range(1, len(price_series))
    ]


def restore_price_from_return(
    base_price: float,
    return_series: list[float],
    use_log: bool = True,
) -> list[float]:
    """
    由收益率序列还原价格路径。

    Args:
        base_price: 基准价格（起点）。
        return_series: 收益率序列。
        use_log: True 表示对数收益率，False 表示简单收益率。

    Returns:
        还原后的预测价格序列。
    """
    prices = []
    current = base_price
    for r in return_series:
        if use_log:
            current = current * math.exp(r)
        else:
            current = current * (1 + r)
        prices.append(round(current, 4))
    return prices


def clip(value: float, min_val: float, max_val: float) -> float:
    """
    将数值裁剪到 [min_val, max_val] 区间。

    Args:
        value: 原始值。
        min_val: 最小值。
        max_val: 最大值。

    Returns:
        裁剪后的值。
    """
    return max(min_val, min(max_val, value))


def safe_divide(numerator: float, denominator: float, fallback: float = 0.0) -> float:
    """
    安全除法，分母为零时返回 fallback。

    Args:
        numerator: 分子。
        denominator: 分母。
        fallback: 除零时的返回值。

    Returns:
        计算结果或 fallback。
    """
    if denominator == 0:
        return fallback
    return numerator / denominator
