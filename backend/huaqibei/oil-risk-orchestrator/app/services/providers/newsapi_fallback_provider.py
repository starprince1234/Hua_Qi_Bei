"""NewsAPI provider for live fallback oil-market articles."""

from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import httpx

from ...core.settings import settings
from ...repositories.protocols import EventRepository, JsonObject
from ...schemas.intelligence_schema import NewsEventItem, NewsEventListResponse

NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"
DEFAULT_NEWS_QUERY = (
    '(oil OR crude OR Brent OR WTI OR OPEC OR "energy market" OR refinery '
    'OR sanctions OR "Red Sea" OR tanker)'
)
OIL_KEYWORDS = [
    "oil",
    "crude",
    "brent",
    "wti",
    "opec",
    "saudi",
    "russia",
    "sanction",
    "refinery",
    "tanker",
    "red sea",
    "inventory",
    "eia",
]
BEARISH_TERMS = ["surplus", "stockpile", "inventory build", "demand weak", "ceasefire", "output hike"]
BULLISH_TERMS = ["sanction", "attack", "disruption", "cut", "shortage", "tension", "conflict", "outage"]


class NewsAPIFallbackProvider:
    """Fetch and normalize oil-market articles from NewsAPI."""

    def __init__(
        self,
        api_key: str | None = None,
        timeout_seconds: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._client = client

    @property
    def provider_status(self) -> str:
        """Return the provider identity for diagnostics and orchestration."""
        return "newsapi"

    def get_events(self, filters: dict[str, object] | None = None) -> NewsEventListResponse:
        """Return filtered NewsAPI articles as dashboard news events."""
        api_key = self._api_key or settings.NEWSAPI_API_KEY
        if not api_key:
            raise RuntimeError("NEWSAPI_API_KEY is required when NEWS_PROVIDER uses NewsAPI.")

        normalized_filters = filters or {}
        params = self._build_params(normalized_filters, api_key)
        payload = self._request(params)
        articles = payload.get("articles", [])
        article_objects = articles if isinstance(articles, list) else []
        items = [
            self._article_to_event(article, index)
            for index, article in enumerate(article_objects)
            if isinstance(article, dict)
        ]
        filtered_items = self._filter_events(items, normalized_filters)
        return NewsEventListResponse(
            items=filtered_items,
            updated_at=_utc_now(),
            provider_status="newsapi_live",
        )

    def list_events(self, filters: dict[str, object] | None = None) -> NewsEventListResponse:
        """Repository-compatible alias for ``get_events``."""
        return self.get_events(filters)

    def get_event(self, event_id: str) -> NewsEventItem | None:
        """Live single-event lookup is intentionally not supported without a cache."""
        _ = event_id
        return None

    def upsert_event(self, event: NewsEventItem, raw_payload: JsonObject | None = None) -> NewsEventItem:
        """NewsAPI is a read-only provider; persistence belongs to a repository adapter."""
        _ = raw_payload
        return event

    def _build_params(self, filters: dict[str, object], api_key: str) -> dict[str, str | int]:
        keyword = str(filters.get("keyword") or "").strip()
        query = f"({keyword}) AND {DEFAULT_NEWS_QUERY}" if keyword else DEFAULT_NEWS_QUERY
        params: dict[str, str | int] = {
            "apiKey": api_key,
            "q": query[:500],
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(_to_non_negative_int(filters.get("limit"), 20), 100),
            "page": 1 + (_to_non_negative_int(filters.get("offset"), 0) // 100),
        }
        from_date = str(filters.get("from_date") or "").strip()
        to_date = str(filters.get("to_date") or "").strip()
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return params

    def _request(self, params: dict[str, str | int]) -> dict[str, Any]:
        if self._client is not None:
            response = self._client.get(NEWSAPI_EVERYTHING_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        else:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.get(NEWSAPI_EVERYTHING_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        if not isinstance(payload, dict):
            raise RuntimeError("NewsAPI returned a non-object response.")
        if payload.get("status") == "error":
            message = str(payload.get("message") or "NewsAPI request failed.")
            raise RuntimeError(message)
        return payload

    def _article_to_event(self, article: dict[str, Any], index: int) -> NewsEventItem:
        url = _clean_str(article.get("url"))
        title = _clean_str(article.get("title")) or "Untitled oil-market article"
        summary = _clean_str(article.get("description")) or _clean_str(article.get("content")) or title
        published_at = _clean_str(article.get("publishedAt")) or _utc_now()
        source_payload = article.get("source")
        source_name = ""
        if isinstance(source_payload, dict):
            source_name = _clean_str(source_payload.get("name"))
        direction, score, confidence = _infer_impact(title, summary)
        provider_id = sha256(f"{url}|{published_at}|{title}".encode("utf-8")).hexdigest()[:16]
        return NewsEventItem(
            event_id=f"newsapi_{provider_id}",
            published_at=published_at,
            source="newsapi",
            provider_event_id=provider_id or f"article_{index}",
            title=title,
            summary=summary,
            url=url,
            impact_direction=direction,
            impact_score=score,
            confidence=confidence,
            affected_industries=_affected_industries(title, summary),
            tags=_extract_tags(title, summary, extra=[source_name]),
            llm_model_id="rule-based-newsapi-v1",
            analysis_version="newsapi-rule-v1",
        )

    def _filter_events(
        self,
        items: list[NewsEventItem],
        filters: dict[str, object],
    ) -> list[NewsEventItem]:
        source = filters.get("source")
        if source and source != "all" and source != "newsapi":
            return []

        impact_direction = filters.get("impact_direction")
        if impact_direction:
            items = [item for item in items if item.impact_direction == impact_direction]

        impact_level = filters.get("impact_level")
        if impact_level:
            items = [item for item in items if _matches_impact_level(item.impact_score, str(impact_level))]

        return items


def _infer_impact(title: str, summary: str) -> tuple[str, int, float]:
    text = f"{title} {summary}".lower()
    bullish_hits = sum(1 for term in BULLISH_TERMS if term in text)
    bearish_hits = sum(1 for term in BEARISH_TERMS if term in text)
    if bullish_hits > bearish_hits:
        return "bullish", min(10, 5 + bullish_hits), min(0.85, 0.55 + bullish_hits * 0.08)
    if bearish_hits > bullish_hits:
        return "bearish", min(10, 5 + bearish_hits), min(0.85, 0.55 + bearish_hits * 0.08)
    return "neutral", 3, 0.45


def _affected_industries(title: str, summary: str) -> list[str]:
    text = f"{title} {summary}".lower()
    industries = ["refining", "shipping", "petrochemicals"]
    if "airline" in text or "aviation" in text or "jet fuel" in text:
        industries.append("aviation")
    if "freight" in text or "tanker" in text or "red sea" in text:
        industries.append("logistics")
    return industries


def _extract_tags(title: str, summary: str, extra: list[str] | None = None) -> list[str]:
    text = f"{title} {summary}".lower()
    tags = [keyword.upper() if keyword in {"opec", "wti", "eia"} else keyword.title() for keyword in OIL_KEYWORDS if keyword in text]
    for value in extra or []:
        if value and value not in tags:
            tags.append(value)
    return tags[:8]


def _matches_impact_level(score: int, level: str) -> bool:
    if level == "high":
        return score >= 7
    if level == "medium":
        return 4 <= score <= 6
    if level == "low":
        return score <= 3
    return True


def _to_non_negative_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)


def _clean_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


newsapi_event_repository: EventRepository = NewsAPIFallbackProvider()
