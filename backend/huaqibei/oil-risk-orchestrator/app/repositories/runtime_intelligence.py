"""Runtime online intelligence store fed by successful prediction runs."""

from __future__ import annotations

from datetime import UTC, datetime

from app.schemas.intelligence_schema import (
    BacktestErrorsResponse,
    BacktestMetrics,
    BacktestSeriesResponse,
    BacktestSummaryResponse,
    FactorHistoryPoint,
    FactorHistoryResponse,
    OverviewBacktestStatus,
    OverviewDominantFactor,
    OverviewPredictionSummary,
)
from app.schemas.report_schema import PredictResultPayload


FACTOR_CATEGORIES = ["inventory", "geo", "macro", "supply_demand", "technical"]
BACKTEST_REQUIRED_FIELDS = [
    "as_of_date",
    "target",
    "actual_price",
    "actual_return_7d",
    "predicted_price",
    "predicted_return_7d",
    "lower_return_7d",
    "upper_return_7d",
    "model_version",
    "run_id",
]


class RuntimeIntelligenceStore:
    """In-process online data generated after file upload and model inference."""

    def __init__(self) -> None:
        self._factor_points: list[FactorHistoryPoint] = []
        self._latest_prediction: OverviewPredictionSummary = OverviewPredictionSummary()
        self._latest_factor: OverviewDominantFactor = OverviewDominantFactor()

    def record_prediction(self, payload: PredictResultPayload) -> None:
        """Capture the latest prediction and append one factor contribution point."""
        now = _utc_now()
        prediction = payload.prediction
        q05 = prediction.return_quantiles.get("0.05")
        q50 = prediction.return_quantiles.get("0.5")
        q95 = prediction.return_quantiles.get("0.95")
        contribution_map = _aggregate_factor_categories(
            {
                item.factor: item.contribution
                for item in payload.explainability.top_factors
            }
        )
        dominant_key, dominant_value = _dominant_factor(contribution_map)

        self._latest_prediction = OverviewPredictionSummary(
            available=True,
            updated_at=now,
            model_version=prediction.model_version,
            risk_level=prediction.risk_level,
            horizon=prediction.horizon,
            confidence_score=prediction.confidence_score,
            median_return=q50,
        )
        self._latest_factor = OverviewDominantFactor(
            category=dominant_key,
            contribution=dominant_value,
            label=_factor_label(dominant_key),
        )
        self._factor_points.append(
            FactorHistoryPoint(
                date=now,
                inventory=contribution_map["inventory"],
                geo=contribution_map["geo"],
                macro=contribution_map["macro"],
                supply_demand=contribution_map["supply_demand"],
                technical=contribution_map["technical"],
                event_label="Latest online prediction",
                predicted_return_7d=q50 or 0.0,
                lower_return_7d=q05 or 0.0,
                upper_return_7d=q95 or 0.0,
                actual_return_7d=None,
                hit_interval=None,
            )
        )

    def get_latest_prediction(self) -> OverviewPredictionSummary:
        return self._latest_prediction

    def get_dominant_factor(self) -> OverviewDominantFactor:
        return self._latest_factor

    def get_backtest_summary(self, target: str) -> BacktestSummaryResponse:
        return BacktestSummaryResponse(
            target=target,
            window="",
            metrics=BacktestMetrics(
                direction_accuracy=0.0,
                rmse=0.0,
                mape=0.0,
                interval_hit_rate={},
            ),
            stage_metrics=[],
            provider_status="online_empty",
            required_fields=BACKTEST_REQUIRED_FIELDS,
            message=(
                "No online backtest dataset has been imported yet. Upload historical rows "
                "with actual outcomes and prediction intervals to compute validation metrics."
            ),
        )

    def get_backtest_series(self, _target: str) -> BacktestSeriesResponse:
        return BacktestSeriesResponse(points=[], events=[])

    def get_backtest_errors(self, _target: str) -> BacktestErrorsResponse:
        return BacktestErrorsResponse(bins=[])

    def get_factor_history(
        self,
        _target: str,
        from_date: str | None = None,
        to_date: str | None = None,
        _granularity: str | None = None,
    ) -> FactorHistoryResponse:
        points = [
            point
            for point in self._factor_points
            if _date_in_range(point.date, from_date, to_date)
        ]
        return FactorHistoryResponse(
            categories=FACTOR_CATEGORIES,
            points=points,
            provider_status="online_prediction_history",
        )

    def get_backtest_status(self) -> OverviewBacktestStatus:
        return OverviewBacktestStatus(
            provider_status="online_empty",
            available=False,
            point_count=0,
            required_fields=BACKTEST_REQUIRED_FIELDS,
        )


def _aggregate_factor_categories(raw_contributions: dict[str, float]) -> dict[str, float]:
    buckets = {category: 0.0 for category in FACTOR_CATEGORIES}
    for factor, contribution in raw_contributions.items():
        category = _categorize_factor(factor)
        buckets[category] += abs(float(contribution))

    total = sum(buckets.values())
    if total <= 0:
        buckets["technical"] = 1.0
        return buckets
    return {key: round(value / total, 6) for key, value in buckets.items()}


def _categorize_factor(factor: str) -> str:
    text = factor.lower()
    if any(token in text for token in ["inventory", "stock", "eia", "库存"]):
        return "inventory"
    if any(token in text for token in ["opec", "sanction", "russia", "saudi", "red sea", "地缘"]):
        return "geo"
    if any(token in text for token in ["dxy", "t5yie", "rate", "inflation", "treasury", "宏观"]):
        return "macro"
    if any(token in text for token in ["gasoline", "crack", "supply", "demand", "refinery", "供需"]):
        return "supply_demand"
    return "technical"


def _dominant_factor(contributions: dict[str, float]) -> tuple[str | None, float | None]:
    if not contributions:
        return None, None
    category = max(contributions, key=lambda key: contributions[key])
    return category, contributions[category]


def _factor_label(category: str | None) -> str | None:
    labels = {
        "inventory": "Inventory",
        "geo": "Geopolitical",
        "macro": "Macro",
        "supply_demand": "Supply / Demand",
        "technical": "Technical",
    }
    return labels.get(category or "")


def _date_in_range(value: str, from_date: str | None, to_date: str | None) -> bool:
    value_date = _parse_date(value)
    start = _parse_date(from_date)
    end = _parse_date(to_date)
    if value_date is None:
        return False
    if start is not None and end is not None and start > end:
        return False
    if start is not None and value_date < start:
        return False
    if end is not None and value_date > end:
        return False
    return True


def _parse_date(value: str | None):
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        try:
            return datetime.fromisoformat(value[:10]).date()
        except ValueError:
            return None


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


runtime_intelligence_store = RuntimeIntelligenceStore()
