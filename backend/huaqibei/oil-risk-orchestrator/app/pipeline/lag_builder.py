"""
滞后特征构建管道节点：为时间序列添加滞后期特征
"""
from __future__ import annotations

from typing import List

import pandas as pd


def add_lag_features(
    df: pd.DataFrame,
    columns: List[str],
    lags: List[int],
) -> pd.DataFrame:
    """
    为指定列添加滞后期特征。

    Parameters
    ----------
    df:
        原始 DataFrame，按时间升序排列。
    columns:
        需要生成滞后特征的列名列表。
    lags:
        滞后期数列表，例如 ``[1, 3, 5]``。

    Returns
    -------
    pd.DataFrame
        新增了滞后特征列的 DataFrame（原列保留）。
    """
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        for lag in lags:
            df[f"{col}_lag{lag}"] = df[col].shift(lag)
    return df


def add_rolling_features(
    df: pd.DataFrame,
    columns: List[str],
    windows: List[int],
) -> pd.DataFrame:
    """
    为指定列添加滚动统计特征（均值和标准差）。

    Parameters
    ----------
    df:
        原始 DataFrame，按时间升序排列。
    columns:
        需要生成滚动特征的列名列表。
    windows:
        窗口大小列表，例如 ``[5, 10, 20]``。

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            continue
        for w in windows:
            df[f"{col}_roll_mean_{w}"] = df[col].rolling(w).mean()
            df[f"{col}_roll_std_{w}"] = df[col].rolling(w).std()
    return df


def drop_lag_na_rows(df: pd.DataFrame) -> pd.DataFrame:
    """删除因滞后或滚动操作产生空值的行。"""
    return df.dropna()
