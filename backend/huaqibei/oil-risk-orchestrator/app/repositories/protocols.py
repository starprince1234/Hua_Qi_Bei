"""Protocol-only persistence seams for intelligence data.

These interfaces describe the storage boundary for future PostgreSQL and Redis
adapters. They intentionally avoid importing database clients so route and
service modules can depend on the seams without requiring live infrastructure.
"""

from __future__ import annotations

from typing import Protocol, TypeAlias

from ..schemas.intelligence_schema import (
    BacktestErrorsResponse,
    BacktestSeriesResponse,
    BacktestSummaryResponse,
    FactorHistoryResponse,
    NewsEventItem,
    NewsEventListResponse,
)

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]


class EventRepository(Protocol):
    """Storage contract for enriched oil-market news events."""

    def list_events(self, filters: dict[str, object] | None = None) -> NewsEventListResponse:
        """Return filtered events with cache/provider freshness metadata."""
        ...

    def get_event(self, event_id: str) -> NewsEventItem | None:
        """Return one enriched event by internal ID, or None when absent."""
        ...

    def upsert_event(self, event: NewsEventItem, raw_payload: JsonObject | None = None) -> NewsEventItem:
        """Insert or update an event and preserve optional provider payload for audit."""
        ...


class BacktestRepository(Protocol):
    """Storage contract for backtest summaries, series, and error bins."""

    def get_summary(self, target: str) -> BacktestSummaryResponse:
        """Return the latest summary for a target such as Brent or WTI."""
        ...

    def get_series(self, target: str) -> BacktestSeriesResponse:
        """Return actual-vs-predicted price series and event markers."""
        ...

    def get_errors(self, target: str) -> BacktestErrorsResponse:
        """Return prediction error histogram bins for the latest run."""
        ...

    def save_backtest(
        self,
        summary: BacktestSummaryResponse,
        series: BacktestSeriesResponse,
        errors: BacktestErrorsResponse,
        *,
        provider_status: str,
        model_version: str | None = None,
    ) -> None:
        """Persist one backtest payload set from an offline run or demo seed."""
        ...


class FactorRepository(Protocol):
    """Storage contract for historical factor contribution data."""

    def get_history(
        self,
        target: str,
        from_date: str | None = None,
        to_date: str | None = None,
        granularity: str | None = None,
    ) -> FactorHistoryResponse:
        """Return contribution history using the same filters as the API route."""
        ...

    def save_history(
        self,
        target: str,
        history: FactorHistoryResponse,
        *,
        provider_status: str,
        run_id: str | None = None,
    ) -> None:
        """Persist factor contribution points for a target and optional model run."""
        ...


class CacheProvider(Protocol):
    """Minimal cache adapter seam for Redis, in-memory, or no-op caches."""

    def get_json(self, key: str) -> JsonObject | list[JsonValue] | None:
        """Return decoded JSON-compatible cached value, or None on cache miss."""
        ...

    def set_json(
        self,
        key: str,
        value: JsonObject | list[JsonValue],
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        """Store a JSON-compatible value with an optional expiry."""
        ...

    def delete(self, key: str) -> None:
        """Delete one cached value when present."""
        ...

    def get_status(self, namespace: str) -> str:
        """Return provider status such as demo, gdelt_cached, or stale_cache."""
        ...
