"""Schemas for news events, backtest validation, and factor history."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, computed_field


class NewsEventItem(BaseModel):
    """Single oil-market intelligence event enriched for display."""

    event_id: str = Field(..., description="Internal event ID")
    published_at: str = Field(..., description="Published time in ISO8601 format")
    source: Literal["gdelt", "newsapi", "demo"] = Field(..., description="News source provider")
    provider_event_id: str = Field(..., description="Provider-side event ID")
    title: str = Field(..., description="Event title")
    summary: str = Field(..., description="Event summary")
    url: str = Field(..., description="Original article URL")
    impact_direction: Literal["bullish", "bearish", "neutral"] = Field(
        ...,
        description="Expected oil price impact direction",
    )
    impact_score: int = Field(..., ge=0, le=10, description="Impact score from 0 to 10")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Analysis confidence from 0 to 1")
    affected_industries: list[str] = Field(..., description="Affected downstream industries")
    tags: list[str] = Field(..., description="Event tags")
    llm_model_id: str = Field(..., description="LLM model used for enrichment")
    analysis_version: str = Field(..., description="Analysis schema or prompt version")

    @computed_field
    @property
    def impact_level(self) -> str:
        """Return the display impact bucket derived from the impact score."""

        if self.impact_score >= 7:
            return "high"
        if self.impact_score >= 4:
            return "medium"
        return "low"


class NewsEventListResponse(BaseModel):
    """News event list response payload."""

    items: list[NewsEventItem] = Field(..., description="Filtered news events")
    updated_at: str = Field(..., description="Data refresh time in ISO8601 format")
    provider_status: Literal[
        "demo",
        "mock",
        "gdelt_live",
        "newsapi_live",
        "hybrid_live",
        "gdelt_cached",
        "stale_cache",
        "newsapi_fallback",
    ] = Field(..., description="Provider/cache status")


class BacktestMetrics(BaseModel):
    """Aggregate backtest metrics."""

    direction_accuracy: float = Field(..., description="Directional accuracy")
    rmse: float = Field(..., description="Root mean squared error")
    mape: float = Field(..., description="Mean absolute percentage error")
    interval_hit_rate: dict[str, float] = Field(..., description="Hit rate by interval/risk bucket")


class BacktestStageMetric(BaseModel):
    """Backtest metrics for one market regime."""

    stage: str = Field(..., description="Market regime label")
    direction_accuracy: float = Field(..., description="Directional accuracy")
    rmse: float = Field(..., description="Root mean squared error")


class BacktestSummaryResponse(BaseModel):
    """Backtest summary response payload."""

    target: str = Field(..., description="Backtest target, such as Brent or WTI")
    window: str = Field(..., description="Backtest date window")
    metrics: BacktestMetrics = Field(..., description="Aggregate metrics")
    stage_metrics: list[BacktestStageMetric] = Field(..., description="Metrics by market regime")
    provider_status: str = Field(default="online_empty", description="Backtest data provider status")
    run_id: str | None = Field(default=None, description="Stable validation run identifier")
    model_version: str | None = Field(default=None, description="Model or baseline version used for validation")
    updated_at: str | None = Field(default=None, description="Validation payload generation time")
    required_fields: list[str] = Field(default_factory=list, description="Missing fields required to compute a real backtest")
    message: str | None = Field(default=None, description="Human-readable availability note")


class BacktestSeriesPoint(BaseModel):
    """One point in the historical actual-vs-predicted series."""

    date: str = Field(..., description="Point date")
    actual_price: float = Field(..., description="Actual oil price")
    predicted_price: float = Field(..., description="Predicted oil price")
    lower_price: float = Field(..., description="Prediction interval lower price")
    upper_price: float = Field(..., description="Prediction interval upper price")


class BacktestEventMark(BaseModel):
    """Annotated event marker in a backtest series."""

    date: str = Field(..., description="Event date")
    label: str = Field(..., description="Event label")
    hit_interval: bool = Field(..., description="Whether actual return hit the predicted interval")
    actual_return_7d: float = Field(..., description="Actual seven-day return")
    predicted_return_7d: float = Field(..., description="Predicted seven-day return")


class BacktestSeriesResponse(BaseModel):
    """Backtest time series response payload."""

    points: list[BacktestSeriesPoint] = Field(..., description="Backtest series points")
    events: list[BacktestEventMark] = Field(..., description="Annotated event markers")
    provider_status: str = Field(default="online_empty", description="Backtest data provider status")
    run_id: str | None = Field(default=None, description="Stable validation run identifier")
    updated_at: str | None = Field(default=None, description="Validation payload generation time")


class BacktestErrorBin(BaseModel):
    """One histogram bin for prediction errors."""

    range: str = Field(..., description="Error range label")
    count: int = Field(..., description="Number of points in the bin")


class BacktestErrorsResponse(BaseModel):
    """Backtest error distribution response payload."""

    bins: list[BacktestErrorBin] = Field(..., description="Error histogram bins")
    provider_status: str = Field(default="online_empty", description="Backtest data provider status")
    run_id: str | None = Field(default=None, description="Stable validation run identifier")
    updated_at: str | None = Field(default=None, description="Validation payload generation time")


class FactorHistoryPoint(BaseModel):
    """Historical contribution point by factor category."""

    date: str = Field(..., description="Point date")
    inventory: float = Field(..., description="Inventory factor contribution")
    geo: float = Field(..., description="Geopolitical factor contribution")
    macro: float = Field(..., description="Macro factor contribution")
    supply_demand: float = Field(..., description="Supply-demand factor contribution")
    technical: float = Field(..., description="Technical factor contribution")
    event_label: str | None = Field(None, description="Optional event label")
    predicted_return_7d: float = Field(..., description="Predicted seven-day return")
    lower_return_7d: float = Field(..., description="Prediction interval lower return")
    upper_return_7d: float = Field(..., description="Prediction interval upper return")
    actual_return_7d: float | None = Field(None, description="Actual seven-day return when labeled history is available")
    hit_interval: bool | None = Field(None, description="Whether actual return hit the predicted interval")


class FactorHistoryResponse(BaseModel):
    """Factor contribution history response payload."""

    categories: list[str] = Field(..., description="Factor category keys")
    points: list[FactorHistoryPoint] = Field(..., description="Historical contribution points")
    provider_status: str = Field(default="online_prediction_history", description="Factor data provider status")
    run_id: str | None = Field(default=None, description="Stable validation run identifier")
    updated_at: str | None = Field(default=None, description="Factor history payload generation time")


class OverviewEventSummary(BaseModel):
    """Compact event summary for the overview page."""

    title: str = ""
    impact_direction: str = "neutral"
    impact_level: str = "low"
    published_at: str | None = None
    source: str | None = None


class OverviewPredictionSummary(BaseModel):
    """Latest prediction summary captured from a successful online inference."""

    available: bool = False
    updated_at: str | None = None
    model_version: str | None = None
    risk_level: str | None = None
    horizon: int | None = None
    confidence_score: float | None = None
    median_return: float | None = None


class OverviewDominantFactor(BaseModel):
    """Dominant factor category derived from latest prediction contributions."""

    category: str | None = None
    contribution: float | None = None
    label: str | None = None


class OverviewBacktestStatus(BaseModel):
    """Backtest data availability for the overview page."""

    provider_status: str = "online_empty"
    available: bool = False
    point_count: int = 0
    required_fields: list[str] = Field(default_factory=list)
    run_id: str | None = None
    updated_at: str | None = None


class OverviewResponse(BaseModel):
    """Aggregated online data used by the overview page."""

    updated_at: str
    news_provider_status: str
    news_event_count: int = 0
    high_impact_event: OverviewEventSummary | None = None
    latest_prediction: OverviewPredictionSummary = Field(default_factory=OverviewPredictionSummary)
    dominant_factor: OverviewDominantFactor = Field(default_factory=OverviewDominantFactor)
    factor_history_points: int = 0
    backtest: OverviewBacktestStatus = Field(default_factory=OverviewBacktestStatus)
