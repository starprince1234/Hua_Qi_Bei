"""Tests for intelligence schemas and provider abstractions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.main import create_app
from app.schemas.intelligence_schema import NewsEventItem, NewsEventListResponse
from app.services.intelligence_service import (
    DemoProvider,
    HybridNewsProvider,
    IntelligenceService,
    build_intelligence_provider,
)
from app.services.providers.gdelt_provider import GDELTProvider
from app.services.providers.newsapi_fallback_provider import NewsAPIFallbackProvider
from app.repositories.runtime_intelligence import RuntimeIntelligenceStore
from app.schemas.report_schema import (
    AIRiskInsight,
    AIIndustryInsight,
    AIKnowledgeGraphInsight,
    AIReportInsight,
    AIInsightsBlock,
    DataProcessingLogV1,
    ExplainabilityBlock,
    FactorContributionV1,
    FactorSelectionReasons,
    FuturePathBlock,
    KnowledgeGraphBlock,
    PredictResultPayload,
    PredictionSummaryV1,
    ReportResult,
    RiskReportSections,
    ShockSignal,
)


def valid_news_event_payload() -> dict[str, Any]:
    return {
        "event_id": "evt_test_001",
        "published_at": "2026-06-07T08:30:00Z",
        "source": "demo",
        "provider_event_id": "demo_evt_test_001",
        "title": "Demo title",
        "summary": "Demo summary",
        "url": "https://example.com/demo",
        "impact_direction": "bullish",
        "impact_score": 8,
        "confidence": 0.82,
        "affected_industries": ["aviation"],
        "tags": ["OPEC"],
        "llm_model_id": "Pro/deepseek-ai/DeepSeek-V3.2",
        "analysis_version": "demo-v1",
    }


def test_news_event_schema_accepts_valid_payload() -> None:
    item = NewsEventItem(**valid_news_event_payload())

    assert item.source == "demo"
    assert item.impact_direction == "bullish"
    assert item.impact_score == 8


def test_news_event_schema_rejects_invalid_enum_values() -> None:
    payload = valid_news_event_payload()
    payload["source"] = "rss"

    with pytest.raises(ValidationError):
        NewsEventItem(**payload)


def test_news_event_schema_rejects_out_of_range_score() -> None:
    payload = valid_news_event_payload()
    payload["impact_score"] = 11

    with pytest.raises(ValidationError):
        NewsEventItem(**payload)


def test_news_event_list_rejects_invalid_provider_status() -> None:
    payload = {
        "items": [valid_news_event_payload()],
        "updated_at": "2026-06-07T08:40:00Z",
        "provider_status": "live",
    }

    with pytest.raises(ValidationError):
        NewsEventListResponse(**payload)


def test_demo_provider_filters_events_by_direction_level_source_keyword_and_date() -> None:
    provider = DemoProvider()

    response = provider.get_events(
        {
            "impact_direction": "bullish",
            "impact_level": "high",
            "source": "gdelt",
            "keyword": "OPEC",
            "from_date": "2026-06-07",
            "to_date": "2026-06-07",
        }
    )

    assert response.provider_status == "demo"
    assert [item.event_id for item in response.items] == ["evt_20260607_001"]


def test_demo_provider_is_deterministic() -> None:
    provider = DemoProvider()

    first = provider.get_backtest_summary("Brent")
    second = provider.get_backtest_summary("Brent")

    assert first == second
    assert first.metrics.direction_accuracy == 0.723


def test_demo_provider_handles_invalid_date_ranges_gracefully() -> None:
    provider = DemoProvider()

    events = provider.get_events({"from_date": "2026-06-08", "to_date": "2026-06-01"})
    factors = provider.get_factor_history("Brent", "2026-06-08", "2026-06-01", "month")

    assert events.items == []
    assert factors.points == []


class FailingProvider:
    def get_events(self, filters: dict[str, Any] | None = None) -> NewsEventListResponse:
        raise RuntimeError("primary provider failed")

    def get_backtest_summary(self, target: str):
        raise RuntimeError("primary provider failed")

    def get_backtest_series(self, target: str):
        raise RuntimeError("primary provider failed")

    def get_backtest_errors(self, target: str):
        raise RuntimeError("primary provider failed")

    def get_factor_history(
        self,
        target: str,
        from_date: str | None,
        to_date: str | None,
        granularity: str | None,
    ):
        raise RuntimeError("primary provider failed")


def test_intelligence_service_falls_back_to_demo_provider() -> None:
    service = IntelligenceService(provider=FailingProvider(), fallback_provider=DemoProvider())

    events = service.get_events({"impact_direction": "bearish"})
    summary = service.get_backtest_summary("Brent")

    assert events.provider_status == "demo"
    assert all(item.impact_direction == "bearish" for item in events.items)
    assert summary.target == "Brent"


def test_build_intelligence_provider_uses_configured_news_provider() -> None:
    assert isinstance(build_intelligence_provider("mock"), DemoProvider)
    assert isinstance(build_intelligence_provider("newsapi"), NewsAPIFallbackProvider)
    assert isinstance(build_intelligence_provider("gdelt"), GDELTProvider)
    assert isinstance(build_intelligence_provider("hybrid"), HybridNewsProvider)


class FakeNewsAPIResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "articles": [
                {
                    "source": {"name": "Energy Wire"},
                    "title": "OPEC output cut raises crude supply concerns",
                    "description": "Oil markets reacted to a fresh disruption risk.",
                    "url": "https://example.com/opec-cut",
                    "publishedAt": "2026-06-08T01:02:03Z",
                    "content": "Long article body",
                }
            ],
        }


class FakeNewsAPIClient:
    def get(self, url: str, params: dict[str, str | int]):
        self.url = url
        self.params = params
        return FakeNewsAPIResponse()


def test_newsapi_provider_maps_articles_to_news_events() -> None:
    client = FakeNewsAPIClient()
    provider = NewsAPIFallbackProvider(api_key="test-key", client=client)

    response = provider.get_events({"keyword": "OPEC", "limit": 5})

    assert response.provider_status == "newsapi_live"
    assert client.params["pageSize"] == 5
    assert response.items[0].source == "newsapi"
    assert response.items[0].impact_direction == "bullish"
    assert response.items[0].title == "OPEC output cut raises crude supply concerns"
    assert response.items[0].url == "https://example.com/opec-cut"


class FakeQueryJob:
    def result(self):
        return [
            {
                "SQLDATE": 20260608,
                "Actor1Name": "OPEC",
                "Actor2Name": "GLOBAL MARKETS",
                "EventCode": "043",
                "GoldsteinScale": -4.0,
                "AvgTone": -2.0,
                "SOURCEURL": "https://example.com/gdelt-source",
            }
        ]


class FakeBigQueryClient:
    def query(self, query: str, job_config: object | None = None):
        self.query_text = query
        self.job_config = job_config
        return FakeQueryJob()


def test_gdelt_provider_maps_bigquery_rows_to_news_events() -> None:
    client = FakeBigQueryClient()
    provider = GDELTProvider(project_id="test-project", client=client)

    response = provider.get_events({"keyword": "OPEC", "limit": 3})

    assert response.provider_status == "gdelt_live"
    assert "gdelt-bq.gdeltv2.events" in client.query_text
    assert "LIMIT 3" in client.query_text
    assert response.items[0].source == "gdelt"
    assert response.items[0].impact_direction == "bullish"
    assert response.items[0].published_at == "2026-06-08T00:00:00Z"
    assert response.items[0].url == "https://example.com/gdelt-source"


def test_events_route_returns_success_envelope_with_demo_items() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/events")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["code"] == 200
    assert payload["data"]["provider_status"] == "demo"
    assert payload["data"]["updated_at"] == "2026-06-07T08:40:00Z"
    assert len(payload["data"]["items"]) > 0


def test_events_route_filters_by_bullish_impact_direction() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/events", params={"impact_direction": "bullish"})

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) > 0
    assert all(item["impact_direction"] == "bullish" for item in items)


def test_events_route_invalid_date_range_returns_empty_items() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/events",
        params={"from_date": "2026-06-08", "to_date": "2026-06-01"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["items"] == []


def test_backtest_summary_api_returns_direction_accuracy() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/backtest/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["provider_status"] == "offline_validation"
    assert payload["data"]["window"] == "2015-01-01/2025-12-31"
    assert payload["data"]["run_id"].startswith("offline_validation_")
    assert payload["data"]["model_version"] == "ridge_baseline_from_raw_v1"
    assert payload["data"]["metrics"]["direction_accuracy"] > 0.8
    assert payload["data"]["stage_metrics"]
    assert payload["data"]["required_fields"] == []


def test_backtest_series_api_includes_2022_02_24_event_mark() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/backtest/series")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["points"]) > 0
    assert len(data["events"]) > 0
    assert data["provider_status"] == "offline_validation"
    assert data["run_id"].startswith("offline_validation_")
    assert any(event["date"] == "2020-04-20" and event["label"] == "负油价冲击" for event in data["events"])
    assert any(event["date"] == "2022-02-24" and event["label"] == "俄乌战争爆发" for event in data["events"])
    assert any(event["label"] for event in data["events"])


def test_backtest_errors_api_includes_deterministic_bins() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/backtest/errors")

    assert response.status_code == 200
    bins = response.json()["data"]["bins"]
    assert bins
    assert sum(bin_item["count"] for bin_item in bins) > 0


def test_backtest_invalid_target_returns_structured_or_empty_data() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/backtest/summary", params={"target": "not-a-target"})
    payload = response.json()

    assert "success" in payload
    if response.status_code >= 400:
        assert payload["success"] is False
        assert "code" in payload
        assert "message" in payload
    else:
        assert payload["success"] is True
        assert payload["data"]["provider_status"] == "online_empty"
        assert payload["data"]["target"] == "not-a-target"


def test_factor_history_api_returns_categories_and_points() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/factors/history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["categories"] == [
        "inventory",
        "geo",
        "macro",
        "supply_demand",
        "technical",
    ]
    assert payload["data"]["provider_status"] == "offline_validation"
    assert payload["data"]["run_id"].startswith("offline_validation_")
    assert len(payload["data"]["points"]) > 0


def test_factor_history_api_contains_2022_02_24_geo_contribution() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/factors/history")

    assert response.status_code == 200
    points = response.json()["data"]["points"]
    assert any(point["geo"] > 0 for point in points)
    assert any(point["event_label"] for point in points)


def test_factor_history_api_factor_contribution_sums_are_normalized() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/factors/history")

    assert response.status_code == 200
    data = response.json()["data"]
    categories = data["categories"]
    for point in data["points"]:
        contribution_sum = sum(point[category] for category in categories)
        assert 0.99 <= contribution_sum <= 1.01


def test_overview_api_returns_online_status_without_demo_backtest() -> None:
    client = TestClient(create_app())

    response = client.get("/api/v1/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["backtest"]["provider_status"] == "offline_validation"
    assert payload["data"]["backtest"]["available"] is True
    assert payload["data"]["backtest"]["run_id"].startswith("offline_validation_")
    assert payload["data"]["factor_history_points"] > 0
    assert payload["data"]["dominant_factor"]["category"] is not None
    assert payload["data"]["latest_prediction"]["available"] is False


def test_runtime_store_records_prediction_factor_history() -> None:
    empty_generated_dir = Path(__file__).resolve().parent / ".pytest_cache" / "empty-generated"
    empty_generated_dir.mkdir(parents=True, exist_ok=True)
    store = RuntimeIntelligenceStore(generated_dir=empty_generated_dir)
    payload = PredictResultPayload(
        prediction=PredictionSummaryV1(
            horizon=7,
            return_quantiles={"0.05": -0.01, "0.5": 0.02, "0.95": 0.04},
            confidence_score=0.81,
            risk_level="LOW",
            model_version="test-model",
        ),
        future_path=FuturePathBlock(steps=[]),
        shock_signal=ShockSignal(overall_intensity=0.1, alert_level="LOW", top_affected_industries=[]),
        explainability=ExplainabilityBlock(
            top_factors=[
                FactorContributionV1(factor="DXY", contribution=-0.3),
                FactorContributionV1(factor="Gasoline_7日涨跌幅(%)", contribution=0.7),
            ],
            method="test",
        ),
        knowledge_graph=KnowledgeGraphBlock(paths=[]),
        ai_insights=AIInsightsBlock(
            risk=AIRiskInsight(),
            industry=AIIndustryInsight(),
            knowledge_graph=AIKnowledgeGraphInsight(),
            report=AIReportInsight(),
        ),
        factor_selection_reasons=FactorSelectionReasons(),
        report=ReportResult(
            report_id="test-report",
            sections=RiskReportSections(
                executive_summary="",
                trend_and_confidence="",
                key_drivers="",
                industry_impacts="",
                risks_and_limits="",
            ),
        ),
        data_processing_log=DataProcessingLogV1(
            validation_passed=True,
            repair_actions=[],
            asof_alignment=False,
            lag_features_built=True,
        ),
    )

    store.record_prediction(payload)

    history = store.get_factor_history("Brent")
    assert len(history.points) == 1
    assert history.points[0].actual_return_7d is None
    assert store.get_latest_prediction().available is True
    assert store.get_dominant_factor().category == "supply_demand"


def test_factor_history_api_invalid_date_range_returns_empty_points_or_structured_error() -> None:
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/factors/history",
        params={"from_date": "2026-06-08", "to_date": "2026-06-01"},
    )

    payload = response.json()
    if response.status_code == 200:
        assert payload["success"] is True
        assert payload["data"]["points"] == []
    else:
        assert payload["success"] is False
        assert "code" in payload
        assert "message" in payload
