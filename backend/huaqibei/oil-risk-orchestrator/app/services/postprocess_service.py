"""
后处理服务：对模型原始输出进行归一化、裁剪和格式转换
"""
from __future__ import annotations

from typing import Any, Dict, Tuple


def extract_quantiles(raw_response: Dict[str, Any]) -> Tuple[float, float, float]:
    """
    从模型服务响应中提取 q10 / q50 / q90 分位数预测值。

    Parameters
    ----------
    raw_response:
        模型服务 /predict/returns 的原始 JSON 响应体。

    Returns
    -------
    (q10, q50, q90):
        三个分位数对应的回报率预测值。
    """
    prediction = raw_response.get("prediction", {})
    q10 = float(prediction.get("q10", 0.0))
    q50 = float(prediction.get("q50", 0.0))
    q90 = float(prediction.get("q90", 0.0))
    return q10, q50, q90


def clip_return(value: float, min_val: float = -0.5, max_val: float = 0.5) -> float:
    """将预测回报率裁剪到合理区间，避免极端异常值影响下游逻辑。"""
    return max(min_val, min(max_val, value))


def normalize_quantiles(
    q10: float, q50: float, q90: float
) -> Tuple[float, float, float]:
    """对分位数预测值应用裁剪，确保单调性 q10 <= q50 <= q90。"""
    q10 = clip_return(q10)
    q50 = clip_return(q50)
    q90 = clip_return(q90)

    # 保证分位数单调性
    q10 = min(q10, q50, q90)
    q90 = max(q10, q50, q90)
    q50 = max(q10, min(q50, q90))

    return round(q10, 6), round(q50, 6), round(q90, 6)
