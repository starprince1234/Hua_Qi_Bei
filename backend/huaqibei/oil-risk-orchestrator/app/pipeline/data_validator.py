from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


_REQUIRED_COLUMNS: list[str] = []  # Configurable; empty means any column set is accepted
_MAX_MISSING_RATIO: float = 0.3
_MIN_ROWS: int = 10


def validate_dataframe(df: pd.DataFrame) -> ValidationResult:
    result = ValidationResult()

    if df.empty:
        result.errors.append("Uploaded file is empty.")
        return result

    if len(df) < _MIN_ROWS:
        result.warnings.append(f"Dataset has only {len(df)} rows; predictions may be unreliable.")

    # Check required columns
    missing_cols = [c for c in _REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        result.errors.append(f"Required columns missing: {missing_cols}")

    # Check missing value ratio per column
    for col in df.columns:
        ratio = df[col].isna().mean()
        if ratio > _MAX_MISSING_RATIO:
            result.warnings.append(f"Column '{col}' has {ratio:.0%} missing values.")

    # Check for numeric data
    numeric_cols = df.select_dtypes("number").columns.tolist()
    if not numeric_cols:
        result.errors.append("No numeric columns found. Cannot build feature matrix.")

    # Check date index
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            pd.to_datetime(df.index)
        except Exception:
            result.warnings.append("Index could not be parsed as dates. Time-series alignment skipped.")

    return result
