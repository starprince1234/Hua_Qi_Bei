"""
交叉特征构建管道节点：生成特征之间的交互项
"""
from __future__ import annotations

from itertools import combinations
from typing import List, Optional, Tuple

import pandas as pd


def add_pairwise_interactions(
    df: pd.DataFrame,
    columns: List[str],
    operations: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    为列表中的特征两两生成交互特征。

    Parameters
    ----------
    df:
        原始 DataFrame。
    columns:
        参与交互的列名列表。
    operations:
        交互运算列表，可包含 ``"multiply"``（乘积）和 ``"ratio"``（比值）。
        默认仅生成乘积特征。

    Returns
    -------
    pd.DataFrame
        附加了交互特征的 DataFrame。
    """
    if operations is None:
        operations = ["multiply"]

    df = df.copy()
    for col_a, col_b in combinations(columns, 2):
        if col_a not in df.columns or col_b not in df.columns:
            continue
        if "multiply" in operations:
            df[f"{col_a}_x_{col_b}"] = df[col_a] * df[col_b]
        if "ratio" in operations:
            with pd.option_context("mode.use_inf_as_na", True):
                ratio = df[col_a] / df[col_b].replace(0, float("nan"))
            df[f"{col_a}_div_{col_b}"] = ratio

    return df


def add_custom_interaction(
    df: pd.DataFrame,
    col_a: str,
    col_b: str,
    operation: str = "multiply",
    output_col: Optional[str] = None,
) -> pd.DataFrame:
    """
    为两列生成单个自定义交互特征。

    Parameters
    ----------
    df:
        原始 DataFrame。
    col_a, col_b:
        参与交互的两列列名。
    operation:
        ``"multiply"`` 或 ``"ratio"``。
    output_col:
        输出列名，默认由操作类型和列名自动生成。

    Returns
    -------
    pd.DataFrame
    """
    df = df.copy()
    if col_a not in df.columns or col_b not in df.columns:
        return df

    if output_col is None:
        sep = "x" if operation == "multiply" else "div"
        output_col = f"{col_a}_{sep}_{col_b}"

    if operation == "multiply":
        df[output_col] = df[col_a] * df[col_b]
    elif operation == "ratio":
        with pd.option_context("mode.use_inf_as_na", True):
            df[output_col] = df[col_a] / df[col_b].replace(0, float("nan"))
    else:
        raise ValueError(f"不支持的交互运算: {operation}")

    return df
