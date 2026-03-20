from __future__ import annotations

SUPPORTED_HORIZONS: list[int] = [1, 3, 7, 14, 30]
SUPPORTED_INDUSTRIES: list[str] = ["aviation", "shipping", "chemical"]
REPORT_STYLES: list[str] = ["banking", "general"]

MAX_UPLOAD_MB: int = 50
UPLOAD_DIR: str = "/tmp/oil_risk_uploads"

ALLOWED_EXTENSIONS: set[str] = {".csv", ".parquet", ".xls", ".xlsx"}

# Risk level thresholds (annualised volatility proxy)
RISK_THRESHOLDS: dict[str, float] = {
    "low": 0.10,
    "medium": 0.20,
    "high": 0.35,
}

# Default lag periods for feature engineering
DEFAULT_LAGS: list[int] = [1, 3, 5, 7, 14]

# Quantile levels returned by model service
QUANTILE_LEVELS: list[float] = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]

# Industry fuel-cost sensitivity coefficients (rough order-of-magnitude)
INDUSTRY_SENSITIVITY: dict[str, float] = {
    "aviation": 0.35,   # ~35 % of operating cost is fuel
    "shipping": 0.25,   # ~25 %
    "chemical": 0.60,   # ~60 % of feedstock cost linked to oil
}
