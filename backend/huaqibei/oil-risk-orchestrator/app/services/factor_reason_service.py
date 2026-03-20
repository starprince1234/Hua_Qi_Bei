"""
因子原因解释服务：根据 SHAP 贡献值生成可读的驱动因素说明
"""
from __future__ import annotations

from typing import List

from ..schemas.report_schema import ShapContribution

# 特征名称到中文描述的简单映射
_FEATURE_LABELS: dict[str, str] = {
    "sma_5": "5日均价",
    "sma_10": "10日均价",
    "sma_20": "20日均价",
    "ema_12": "12日指数均价",
    "ema_26": "26日指数均价",
    "macd": "MACD 指标",
    "macd_signal": "MACD 信号线",
    "return_1d": "近1日收益率",
    "return_5d": "近5日收益率",
    "vol_5d": "5日波动率",
    "vol_20d": "20日波动率",
}


def generate_factor_reasons(
    contributions: List[ShapContribution],
    top_n: int = 3,
) -> List[str]:
    """
    根据 SHAP 贡献列表生成主要驱动因素的文字说明。

    Parameters
    ----------
    contributions:
        SHAP 贡献列表（已按绝对值降序排列）。
    top_n:
        取前 top_n 个因素生成说明。

    Returns
    -------
    List[str]
        每条说明描述一个驱动因素的方向和影响程度。
    """
    reasons: List[str] = []
    for contrib in contributions[:top_n]:
        label = _FEATURE_LABELS.get(contrib.feature, contrib.feature)
        direction = "上涨" if contrib.shap_value > 0 else "下跌"
        reasons.append(
            f"{label}（当前值: {contrib.feature_value:.4f}）对预测产生了"
            f"{'正向' if contrib.shap_value > 0 else '负向'}影响，"
            f"推动油价 {direction} 压力，贡献值 {contrib.shap_value:+.4f}。"
        )
    return reasons
