"""
风险评估服务
"""
from __future__ import annotations

from typing import Tuple

from ..schemas.request_schema import Horizon

# 各时间窗口的波动率阈值（绝对收益率，无量纲）
_THRESHOLDS: dict[str, tuple[float, float, float]] = {
    Horizon.ONE_DAY:     (0.01, 0.025, 0.05),
    Horizon.THREE_DAY:   (0.015, 0.04, 0.08),
    Horizon.SEVEN_DAY:   (0.02, 0.05, 0.10),
    Horizon.FOURTEEN_DAY: (0.03, 0.07, 0.15),
    Horizon.THIRTY_DAY:  (0.05, 0.10, 0.20),
}


def assess_risk(q10: float, q50: float, q90: float, horizon: str) -> Tuple[str, float]:
    """
    根据分位数预测评估风险等级和归一化风险评分。

    Parameters
    ----------
    q10, q50, q90:
        10%、50%、90% 分位数预测回报率。
    horizon:
        预测时间窗口标识字符串，例如 ``"1D"``。

    Returns
    -------
    (risk_level, risk_score):
        risk_level 为 ``"low"`` / ``"medium"`` / ``"high"`` / ``"extreme"``；
        risk_score 为 [0, 1] 区间的归一化评分。
    """
    spread = abs(q90 - q10)
    downside = abs(min(q10, 0.0))

    low_thr, med_thr, high_thr = _THRESHOLDS.get(
        horizon,
        _THRESHOLDS[Horizon.SEVEN_DAY],
    )

    # 综合评分：70% 权重给下行风险，30% 给价格区间
    raw_score = 0.7 * (downside / high_thr) + 0.3 * (spread / (high_thr * 2))
    risk_score = min(raw_score, 1.0)

    if risk_score < 0.25:
        risk_level = "low"
    elif risk_score < 0.50:
        risk_level = "medium"
    elif risk_score < 0.75:
        risk_level = "high"
    else:
        risk_level = "extreme"

    return risk_level, round(risk_score, 4)
