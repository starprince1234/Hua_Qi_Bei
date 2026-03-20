"""
数据验证管道节点
"""
from __future__ import annotations

from typing import List, Tuple

import pandas as pd


def validate_no_nulls(df: pd.DataFrame, critical_cols: List[str]) -> Tuple[bool, List[str]]:
    """
    检查关键列是否存在空值。

    Parameters
    ----------
    df:
        待验证的 DataFrame。
    critical_cols:
        必须无空值的列名列表。

    Returns
    -------
    (ok, errors):
        ok 为 True 表示验证通过；errors 为错误信息列表。
    """
    errors: List[str] = []
    for col in critical_cols:
        if col not in df.columns:
            errors.append(f"必要列 '{col}' 不存在")
        elif df[col].isnull().any():
            null_count = int(df[col].isnull().sum())
            errors.append(f"列 '{col}' 含 {null_count} 个空值")
    return len(errors) == 0, errors


def validate_numeric(df: pd.DataFrame, numeric_cols: List[str]) -> Tuple[bool, List[str]]:
    """
    检查指定列是否为数值类型。

    Parameters
    ----------
    df:
        待验证的 DataFrame。
    numeric_cols:
        需为数值类型的列名列表。

    Returns
    -------
    (ok, errors)
    """
    errors: List[str] = []
    for col in numeric_cols:
        if col not in df.columns:
            continue
        if not pd.api.types.is_numeric_dtype(df[col]):
            errors.append(f"列 '{col}' 应为数值类型，实际类型: {df[col].dtype}")
    return len(errors) == 0, errors


def validate_min_rows(df: pd.DataFrame, min_rows: int = 30) -> Tuple[bool, str]:
    """检查 DataFrame 是否满足最小行数要求。"""
    if len(df) < min_rows:
        return False, f"数据行数不足，至少需要 {min_rows} 行，当前仅有 {len(df)} 行"
    return True, ""


def run_all_validations(
    df: pd.DataFrame,
    critical_cols: List[str],
    numeric_cols: List[str],
    min_rows: int = 30,
) -> Tuple[bool, List[str]]:
    """
    执行全部验证步骤，返回汇总结果。

    Returns
    -------
    (valid, all_errors)
    """
    all_errors: List[str] = []

    ok, errs = validate_no_nulls(df, critical_cols)
    all_errors.extend(errs)

    ok2, errs2 = validate_numeric(df, numeric_cols)
    all_errors.extend(errs2)

    ok3, err3 = validate_min_rows(df, min_rows)
    if not ok3:
        all_errors.append(err3)

    return len(all_errors) == 0, all_errors
