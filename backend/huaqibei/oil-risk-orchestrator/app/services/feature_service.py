"""
特征工程服务
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np
import pandas as pd


def build_features(df: pd.DataFrame, target_col: str = "close") -> Dict[str, float]:
    """
    从原始 OHLCV DataFrame 构建模型所需的特征字典。

    Parameters
    ----------
    df:
        原始行情数据，至少包含 ``close`` 列，按时间升序排列。
    target_col:
        收盘价列名，默认 ``"close"``。

    Returns
    -------
    Dict[str, float]
        特征名称到最新单行数值的映射（用于推理）。
    """
    df = df.copy()
    col = target_col

    # 简单移动均线
    for window in [5, 10, 20]:
        df[f"sma_{window}"] = df[col].rolling(window).mean()

    # 指数移动均线
    for span in [12, 26]:
        df[f"ema_{span}"] = df[col].ewm(span=span, adjust=False).mean()

    # MACD
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    # 日收益率
    df["return_1d"] = df[col].pct_change(1)
    df["return_5d"] = df[col].pct_change(5)

    # 波动率
    df["vol_5d"] = df["return_1d"].rolling(5).std()
    df["vol_20d"] = df["return_1d"].rolling(20).std()

    # 取最后一行作为预测特征
    latest: pd.Series = df.iloc[-1]
    features: Dict[str, float] = {
        k: float(v) for k, v in latest.items() if isinstance(v, (int, float, np.floating, np.integer))
    }
    return features


def get_feature_names() -> List[str]:
    """返回模型所需的标准特征列名列表。"""
    names: List[str] = []
    for w in [5, 10, 20]:
        names.append(f"sma_{w}")
    for s in [12, 26]:
        names.append(f"ema_{s}")
    names += ["macd", "macd_signal", "return_1d", "return_5d", "vol_5d", "vol_20d"]
    return names
