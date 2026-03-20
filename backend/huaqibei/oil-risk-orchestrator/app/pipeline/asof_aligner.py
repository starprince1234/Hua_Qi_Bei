from __future__ import annotations

import pandas as pd


def align_series(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure the DataFrame has a well-formed DatetimeIndex.
    Missing business-day dates are forward-filled (as-of semantics).
    """
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            return df  # non-time-series data — return as-is

    # Build a complete business-day range and reindex
    bday_range = pd.bdate_range(start=df.index.min(), end=df.index.max())
    df = df.reindex(bday_range)
    df = df.ffill()  # as-of fill: carry last known value forward
    return df


def asof_merge(
    left: pd.DataFrame,
    right: pd.DataFrame,
    left_on: str,
    right_on: str,
    direction: str = "backward",
) -> pd.DataFrame:
    """
    Merge *right* into *left* using pandas merge_asof semantics.

    Args:
        left: Left DataFrame (must be sorted by *left_on*).
        right: Right DataFrame (must be sorted by *right_on*).
        left_on: Column name in left to merge on.
        right_on: Column name in right to merge on.
        direction: 'backward', 'forward', or 'nearest'.

    Returns:
        Merged DataFrame.
    """
    left_sorted = left.sort_values(left_on)
    right_sorted = right.sort_values(right_on)
    return pd.merge_asof(
        left_sorted,
        right_sorted,
        left_on=left_on,
        right_on=right_on,
        direction=direction,
    )
