from __future__ import annotations

from pydantic import BaseModel, Field


class RiskMetrics(BaseModel):
    var_95: float
    cvar_95: float
    volatility: float
    max_drawdown: float | None = None


class ModelPredictResponse(BaseModel):
    predictions: list[float] = Field(..., description="Point predictions for each horizon step")
    quantiles: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Quantile predictions keyed by quantile level string (e.g. '0.05')",
    )
    shap_values: list[list[float]] | None = Field(None, description="SHAP value matrix [samples × features]")
    feature_names: list[str] | None = Field(None, description="Feature names matching shap_values columns")
    risk_metrics: RiskMetrics | None = None
    model_version: str | None = None
