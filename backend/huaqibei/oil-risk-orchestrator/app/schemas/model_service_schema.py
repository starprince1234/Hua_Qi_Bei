from __future__ import annotations

from pydantic import BaseModel, Field


class ModelPredictRequest(BaseModel):
    features: list[list[float]] = Field(..., description="2-D feature matrix [samples × features]")
    feature_names: list[str] = Field(..., description="Column names for the feature matrix")
    horizon: int = Field(..., description="Prediction horizon in days")
    include_shap: bool = Field(True, description="Whether to return SHAP values")
    include_quantiles: bool = Field(True, description="Whether to return prediction quantiles")
    quantile_levels: list[float] = Field(
        default_factory=lambda: [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95],
        description="Quantile levels to compute",
    )
