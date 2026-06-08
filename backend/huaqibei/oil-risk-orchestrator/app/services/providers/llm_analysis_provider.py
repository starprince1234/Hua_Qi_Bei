"""LLM analysis provider adapter seam.

Future live behavior: enrich news events, backtest annotations, and factor
context with structured LLM outputs that are schema-validated before caching.
M1 behavior: return empty backtest payloads and raise clear messages for write
paths. The module performs no LLM SDK import, credential lookup, or network call
at import time.
"""

from __future__ import annotations

from ...repositories.protocols import BacktestRepository
from ...schemas.intelligence_schema import (
    BacktestErrorsResponse,
    BacktestMetrics,
    BacktestSeriesResponse,
    BacktestSummaryResponse,
)


class LLMAnalysisProvider:
    """Import-safe M1 stub for future structured LLM analysis outputs."""

    @property
    def provider_status(self) -> str:
        """Return the provider identity for diagnostics and orchestration."""
        return "llm"

    def get_summary(self, target: str) -> BacktestSummaryResponse:
        """Return an empty-but-valid backtest summary in M1 demo mode."""
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
        )

    def get_series(self, target: str) -> BacktestSeriesResponse:
        """Return no LLM-derived backtest series annotations in M1."""
        _ = target
        return BacktestSeriesResponse(points=[], events=[])

    def get_errors(self, target: str) -> BacktestErrorsResponse:
        """Return no LLM-derived error bins in M1."""
        _ = target
        return BacktestErrorsResponse(bins=[])

    def save_backtest(
        self,
        summary: BacktestSummaryResponse,
        series: BacktestSeriesResponse,
        errors: BacktestErrorsResponse,
        *,
        provider_status: str,
        model_version: str | None = None,
    ) -> None:
        """Defer persistence of LLM analysis artifacts to future adapters."""
        _ = (summary, series, errors, provider_status, model_version)
        raise NotImplementedError(
            "LLMAnalysisProvider.save_backtest is not implemented for M1; "
            + "use the demo provider or a future persisted analysis adapter."
        )


llm_backtest_repository: BacktestRepository = LLMAnalysisProvider()
