"""Service and provider abstractions for intelligence dashboard data."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Protocol, TypeAlias, cast

from app.core.settings import settings
from app.schemas.intelligence_schema import (  # pyright: ignore[reportImplicitRelativeImport]
    BacktestErrorsResponse,
    BacktestSeriesResponse,
    BacktestSummaryResponse,
    FactorHistoryResponse,
    NewsEventItem,
    NewsEventListResponse,
    OverviewEventSummary,
    OverviewResponse,
)
from app.repositories.runtime_intelligence import runtime_intelligence_store
from app.services.providers.gdelt_provider import GDELTProvider
from app.services.providers.newsapi_fallback_provider import NewsAPIFallbackProvider


EventFilters: TypeAlias = dict[str, str | int | None]


class IntelligenceProvider(Protocol):
    """Provider contract for demo, cached, and future external intelligence sources."""

    def get_events(self, filters: EventFilters | None = None) -> NewsEventListResponse: ...

    def get_backtest_summary(self, target: str) -> BacktestSummaryResponse: ...

    def get_backtest_series(self, _target: str) -> BacktestSeriesResponse: ...

    def get_backtest_errors(self, _target: str) -> BacktestErrorsResponse: ...

    def get_factor_history(
        self,
        _target: str,
        from_date: str | None,
        to_date: str | None,
        _granularity: str | None,
    ) -> FactorHistoryResponse: ...


class DemoProvider:
    """Fixture-backed provider used for deterministic offline demos."""

    def __init__(self, data_dir: str | Path | None = None) -> None:
        default_dir = Path(__file__).resolve().parents[2] / "data"
        self._data_dir: Path = Path(data_dir) if data_dir else default_dir

    def get_events(self, filters: EventFilters | None = None) -> NewsEventListResponse:
        payload = self._load_json("demo_events.json")
        items_payload = payload.get("items", [])
        item_objects = cast(list[object], items_payload) if isinstance(items_payload, list) else []
        items = (
            [NewsEventItem.model_validate(item) for item in item_objects]
            if isinstance(items_payload, list)
            else []
        )
        filtered_items = self._filter_events(items, filters or {})
        return NewsEventListResponse.model_validate(
            {
                "items": filtered_items,
                "updated_at": payload.get("updated_at", "2026-06-07T08:40:00Z"),
                "provider_status": "demo",
            }
        )

    def get_backtest_summary(self, target: str) -> BacktestSummaryResponse:
        payload = self._load_json("demo_backtest.json")
        return BacktestSummaryResponse.model_validate(
            {
                "target": payload.get("target", target),
                "window": payload.get("window", ""),
                "metrics": payload.get("metrics", {}),
                "stage_metrics": payload.get("stage_metrics", []),
            }
        )

    def get_backtest_series(self, _target: str) -> BacktestSeriesResponse:
        payload = self._load_json("demo_backtest.json")
        return BacktestSeriesResponse.model_validate(
            {
                "points": payload.get("points", []),
                "events": payload.get("events", []),
            }
        )

    def get_backtest_errors(self, _target: str) -> BacktestErrorsResponse:
        payload = self._load_json("demo_backtest.json")
        return BacktestErrorsResponse.model_validate({"bins": payload.get("bins", [])})

    def get_factor_history(
        self,
        _target: str,
        from_date: str | None,
        to_date: str | None,
        _granularity: str | None,
    ) -> FactorHistoryResponse:
        payload = self._load_json("demo_factor_history.json")
        response = FactorHistoryResponse.model_validate(
            {
                "categories": payload.get("categories", []),
                "points": payload.get("points", []),
            }
        )
        filtered_points = [
            point
            for point in response.points
            if self._date_in_range(point.date, from_date, to_date)
        ]
        return FactorHistoryResponse(categories=response.categories, points=filtered_points)

    def _load_json(self, filename: str) -> dict[str, object]:
        path = self._data_dir / filename
        with path.open("r", encoding="utf-8") as file:
            payload = cast(object, json.load(file))
        if not isinstance(payload, dict):
            return {}
        return cast(dict[str, object], payload)

    def _filter_events(
        self,
        items: list[NewsEventItem],
        filters: EventFilters,
    ) -> list[NewsEventItem]:
        limit = self._to_non_negative_int(filters.get("limit"), default=len(items))
        offset = self._to_non_negative_int(filters.get("offset"), default=0)
        filtered = [item for item in items if self._matches_event_filters(item, filters)]
        return filtered[offset : offset + limit]

    def _matches_event_filters(self, item: NewsEventItem, filters: EventFilters) -> bool:
        impact_direction = filters.get("impact_direction")
        if impact_direction and item.impact_direction != impact_direction:
            return False

        impact_level = filters.get("impact_level")
        if impact_level and not self._matches_impact_level(item.impact_score, str(impact_level)):
            return False

        source = filters.get("source")
        if source and source != "all" and item.source != source:
            return False

        keyword = str(filters.get("keyword") or "").strip().lower()
        if keyword:
            searchable = " ".join([item.title, item.summary, " ".join(item.tags)]).lower()
            if keyword not in searchable:
                return False

        from_date = filters.get("from_date")
        to_date = filters.get("to_date")
        return self._date_in_range(
            value=item.published_at,
            from_date=from_date if isinstance(from_date, str) else None,
            to_date=to_date if isinstance(to_date, str) else None,
        )

    def _matches_impact_level(self, score: int, level: str) -> bool:
        if level == "high":
            return score >= 7
        if level == "medium":
            return 4 <= score <= 6
        if level == "low":
            return score <= 3
        return True

    def _date_in_range(
        self,
        value: str,
        from_date: str | None,
        to_date: str | None,
    ) -> bool:
        value_date = self._parse_date(value)
        start = self._parse_date(from_date)
        end = self._parse_date(to_date)

        if value_date is None:
            return False
        if start is not None and end is not None and start > end:
            return False
        if start is not None and value_date < start:
            return False
        if end is not None and value_date > end:
            return False
        return True

    def _parse_date(self, value: str | None) -> date | None:
        if not value:
            return None
        normalized = str(value).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).date()
        except ValueError:
            try:
                return date.fromisoformat(str(value)[:10])
            except ValueError:
                return None

    def _to_non_negative_int(self, value: str | int | None, default: int) -> int:
        if value is None:
            return default
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return default
        return max(parsed, 0)


class HybridNewsProvider:
    """Use GDELT first, then NewsAPI when GDELT is unavailable or empty."""

    def __init__(
        self,
        primary_provider: IntelligenceProvider | None = None,
        fallback_provider: IntelligenceProvider | None = None,
    ) -> None:
        self._primary_provider = primary_provider or GDELTProvider()
        self._fallback_provider = fallback_provider or NewsAPIFallbackProvider()

    def get_events(self, filters: EventFilters | None = None) -> NewsEventListResponse:
        try:
            primary = self._primary_provider.get_events(filters)
            if primary.items:
                return NewsEventListResponse(
                    items=primary.items,
                    updated_at=primary.updated_at,
                    provider_status="hybrid_live",
                )
        except Exception:
            pass
        return self._fallback_provider.get_events(filters)

    def get_backtest_summary(self, target: str) -> BacktestSummaryResponse:
        return runtime_intelligence_store.get_backtest_summary(target)

    def get_backtest_series(self, _target: str) -> BacktestSeriesResponse:
        return runtime_intelligence_store.get_backtest_series(_target)

    def get_backtest_errors(self, _target: str) -> BacktestErrorsResponse:
        return runtime_intelligence_store.get_backtest_errors(_target)

    def get_factor_history(
        self,
        _target: str,
        from_date: str | None,
        to_date: str | None,
        _granularity: str | None,
    ) -> FactorHistoryResponse:
        return runtime_intelligence_store.get_factor_history(_target, from_date, to_date, _granularity)


def build_intelligence_provider(provider_name: str | None = None) -> IntelligenceProvider:
    """Build the configured provider while keeping demo data as the safe default."""
    normalized = (provider_name or settings.NEWS_PROVIDER or "mock").strip().lower()
    if normalized in {"mock", "demo"}:
        return DemoProvider()
    if normalized == "newsapi":
        return NewsAPIFallbackProvider()
    if normalized == "gdelt":
        return GDELTProvider()
    if normalized == "hybrid":
        return HybridNewsProvider()
    return DemoProvider()


class IntelligenceService:
    """Thin service wrapper with demo fallback for provider failures."""

    def __init__(
        self,
        provider: IntelligenceProvider | None = None,
        fallback_provider: IntelligenceProvider | None = None,
    ) -> None:
        self._provider: IntelligenceProvider = provider or build_intelligence_provider()
        self._fallback_provider: IntelligenceProvider = fallback_provider or DemoProvider()

    def get_events(self, filters: EventFilters | None = None) -> NewsEventListResponse:
        try:
            return self._provider.get_events(filters)
        except Exception:
            return self._fallback_provider.get_events(filters)

    def get_backtest_summary(self, target: str) -> BacktestSummaryResponse:
        return runtime_intelligence_store.get_backtest_summary(target)

    def get_backtest_series(self, target: str) -> BacktestSeriesResponse:
        return runtime_intelligence_store.get_backtest_series(target)

    def get_backtest_errors(self, target: str) -> BacktestErrorsResponse:
        return runtime_intelligence_store.get_backtest_errors(target)

    def get_factor_history(
        self,
        target: str,
        from_date: str | None = None,
        to_date: str | None = None,
        granularity: str | None = None,
    ) -> FactorHistoryResponse:
        return runtime_intelligence_store.get_factor_history(target, from_date, to_date, granularity)

    def get_overview(self) -> OverviewResponse:
        news_provider_status = "unavailable"
        news_count = 0
        high_impact_event: OverviewEventSummary | None = None
        try:
            events = self.get_events({"limit": 10})
            news_provider_status = events.provider_status
            news_count = len(events.items)
            top_event = max(events.items, key=lambda item: item.impact_score, default=None)
            if top_event is not None:
                high_impact_event = OverviewEventSummary(
                    title=top_event.title,
                    impact_direction=top_event.impact_direction,
                    impact_level=top_event.impact_level,
                    published_at=top_event.published_at,
                    source=top_event.source,
                )
        except Exception:
            pass

        factor_history = runtime_intelligence_store.get_factor_history("Brent")
        return OverviewResponse(
            updated_at=datetime.now().replace(microsecond=0).isoformat(),
            news_provider_status=news_provider_status,
            news_event_count=news_count,
            high_impact_event=high_impact_event,
            latest_prediction=runtime_intelligence_store.get_latest_prediction(),
            dominant_factor=runtime_intelligence_store.get_dominant_factor(),
            factor_history_points=len(factor_history.points),
            backtest=runtime_intelligence_store.get_backtest_status(),
        )
