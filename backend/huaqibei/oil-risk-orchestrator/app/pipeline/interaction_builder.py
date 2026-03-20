from __future__ import annotations

import pandas as pd


def build_interactions(df: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """
    Build pairwise multiplicative interaction features.

    Args:
        df: Input DataFrame.
        columns: Columns to use for interactions. Defaults to all numeric columns (capped at 10).

    Returns:
        DataFrame with interaction columns appended.
    """
    numeric_cols = df.select_dtypes("number").columns.tolist()
    if columns is None:
        columns = numeric_cols[:10]
    else:
        columns = [c for c in columns if c in numeric_cols]

    interaction_frames: dict[str, pd.Series] = {}
    for i, col_a in enumerate(columns):
        for col_b in columns[i + 1 :]:
            key = f"{col_a}_x_{col_b}"
            interaction_frames[key] = df[col_a] * df[col_b]

    if interaction_frames:
        df = pd.concat([df, pd.DataFrame(interaction_frames, index=df.index)], axis=1)

    return df
