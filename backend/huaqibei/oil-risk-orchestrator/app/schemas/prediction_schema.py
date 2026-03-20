from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FactorContribution(BaseModel):
    feature: str
    value: float = Field(..., description="SHAP value (signed impact on prediction)")
    direction: Literal["up", "down", "neutral"]
    label: str = Field("", description="Human-readable Chinese label")
    category: str = Field("", description="Factor category in Chinese")
    reason: str = Field("", description="Plain-language explanation")


class IndustryImpactResult(BaseModel):
    industry: str
    impact_score: float
    direction: Literal["up", "down", "neutral"]
    confidence: float
    description: str


class PredictionResponse(BaseModel):
    file_id: str
    horizon: int
    predictions: list[float]
    quantiles: dict[str, list[float]] = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "high", "extreme"]
    var_95: float
    cvar_95: float
    volatility: float
    factor_contributions: list[FactorContribution] = Field(default_factory=list)
    industry_impacts: list[IndustryImpactResult] = Field(default_factory=list)
    ai_insight: str = ""
    report_style: str = "general"
