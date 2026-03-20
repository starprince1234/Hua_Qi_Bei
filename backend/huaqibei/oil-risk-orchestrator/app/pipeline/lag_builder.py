from __future__ import annotations

import pandas as pd


def build_lags(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """
    Append lag features for each specified column.

    Args:
        df: Input time-series DataFrame with a sorted index.
        columns: Columns to lag. Defaults to all numeric columns.
        lags: Lag periods to generate. Defaults to [1, 3, 5, 7].

    Returns:
        DataFrame with lag columns appended (e.g. 'price_lag1', 'price_lag3').
    """
    if lags is None:
        lags = [1, 3, 5, 7]

    numeric_cols = df.select_dtypes("number").columns.tolist()
    if columns is None:
        columns = numeric_cols
    else:
        columns = [c for c in columns if c in numeric_cols]

    lag_frames: dict[str, pd.Series] = {}
    for col in columns:
        for lag in lags:
            lag_frames[f"{col}_lag{lag}"] = df[col].shift(lag)

    if lag_frames:
        df = pd.concat([df, pd.DataFrame(lag_frames, index=df.index)], axis=1)

    return df
