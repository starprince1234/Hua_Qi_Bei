"""GDELT BigQuery provider for live oil-market event signals."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from typing import Any

from ...core.settings import settings
from ...repositories.protocols import EventRepository, JsonObject
from ...schemas.intelligence_schema import NewsEventItem, NewsEventListResponse

DEFAULT_GDELT_KEYWORDS = [
    "oil",
    "crude",
    "brent",
    "wti",
    "opec",
    "saudi",
    "russia",
    "refinery",
    "tanker",
    "energy",
    "sanction",
]


class GDELTProvider:
    """Query GDELT public BigQuery events and normalize them for the dashboard."""

    def __init__(
        self,
        project_id: str | None = None,
        credentials_json: str | None = None,
        max_bytes_billed: int | None = None,
        client: Any | None = None,
    ) -> None:
        self._project_id = project_id
        self._credentials_json = credentials_json
        self._max_bytes_billed = max_bytes_billed
        self._client = client

    @property
    def provider_status(self) -> str:
        """Return the provider identity for diagnostics and orchestration."""
        return "gdelt"

    def get_events(self, filters: dict[str, object] | None = None) -> NewsEventListResponse:
        """Return live GDELT events matching oil-market filters."""
        normalized_filters = filters or {}
        rows = self._query_rows(normalized_filters)
        items = [self._row_to_event(row, index) for index, row in enumerate(rows)]
        items = self._filter_events(items, normalized_filters)
        return NewsEventListResponse(
            items=items,
            updated_at=_utc_now(),
            provider_status="gdelt_live",
        )

    def list_events(self, filters: dict[str, object] | None = None) -> NewsEventListResponse:
        """Repository-compatible alias for ``get_events``."""
        return self.get_events(filters)

    def get_event(self, event_id: str) -> NewsEventItem | None:
        """Live single-event lookup is intentionally not supported without a cache."""
        _ = event_id
        return None

    def upsert_event(self, event: NewsEventItem, raw_payload: JsonObject | None = None) -> NewsEventItem:
        """GDELT is a read-only provider; persistence belongs to a repository adapter."""
        _ = raw_payload
        return event

    def _query_rows(self, filters: dict[str, object]) -> list[Any]:
        client = self._client or self._build_client()
        query = self._build_query(filters)
        job_config = None if self._client is not None else self._build_job_config()
        query_job = client.query(query, job_config=job_config)
        return list(query_job.result())

    def _build_client(self) -> Any:
        project_id = self._project_id or settings.GDELT_BIGQUERY_PROJECT_ID
        if not project_id:
            raise RuntimeError("GDELT_BIGQUERY_PROJECT_ID is required when NEWS_PROVIDER uses GDELT.")

        from google.cloud import bigquery
        from google.oauth2 import service_account

        credentials = None
        credentials_json = self._credentials_json or settings.GDELT_GOOGLE_CREDENTIALS_JSON
        if credentials_json:
            credentials_info = json.loads(credentials_json)
            credentials = service_account.Credentials.from_service_account_info(credentials_info)
        return bigquery.Client(project=project_id, credentials=credentials)

    def _build_job_config(self) -> Any:
        from google.cloud import bigquery

        max_bytes = self._max_bytes_billed or settings.GDELT_BIGQUERY_MAX_BYTES_BILLED
        return bigquery.QueryJobConfig(
            use_legacy_sql=False,
            maximum_bytes_billed=max_bytes,
        )

    def _build_query(self, filters: dict[str, object]) -> str:
        limit = min(_to_non_negative_int(filters.get("limit"), 20), 100)
        keyword = str(filters.get("keyword") or "").strip().lower()
        keywords = [keyword] if keyword else DEFAULT_GDELT_KEYWORDS
        keyword_conditions = [
            f"LOWER(CONCAT(IFNULL(Actor1Name, ''), ' ', IFNULL(Actor2Name, ''), ' ', IFNULL(SOURCEURL, ''))) LIKE '%{_escape_sql_like(term)}%'"
            for term in keywords
            if term
        ]
        keyword_sql = " OR ".join(keyword_conditions) or "TRUE"
        from_date = _compact_date(str(filters.get("from_date") or "")) or _compact_date(
            (datetime.now(UTC) - timedelta(days=7)).date().isoformat()
        )
        to_date = _compact_date(str(filters.get("to_date") or "")) or _compact_date(datetime.now(UTC).date().isoformat())
        return f"""
            SELECT
              SQLDATE,
              Actor1Name,
              Actor2Name,
              EventCode,
              GoldsteinScale,
              AvgTone,
              SOURCEURL
            FROM `gdelt-bq.gdeltv2.events`
            WHERE SQLDATE BETWEEN {from_date} AND {to_date}
              AND ({keyword_sql})
              AND SOURCEURL IS NOT NULL
            ORDER BY SQLDATE DESC
            LIMIT {limit}
        """

    def _row_to_event(self, row: Any, index: int) -> NewsEventItem:
        row_map = _row_to_mapping(row)
        sql_date = str(row_map.get("SQLDATE") or "")
        actor_1 = _clean_str(row_map.get("Actor1Name")) or "Unknown actor"
        actor_2 = _clean_str(row_map.get("Actor2Name")) or "market counterpart"
        event_code = _clean_str(row_map.get("EventCode")) or "unknown"
        goldstein = _to_float(row_map.get("GoldsteinScale"), 0.0)
        tone = _to_float(row_map.get("AvgTone"), 0.0)
        source_url = _clean_str(row_map.get("SOURCEURL"))
        provider_id = sha256(f"{sql_date}|{actor_1}|{actor_2}|{event_code}|{source_url}".encode("utf-8")).hexdigest()[:16]
        direction, score, confidence = _infer_gdelt_impact(goldstein, tone)
        title = f"GDELT event {event_code}: {actor_1} / {actor_2}"
        summary = (
            f"GDELT recorded an oil-market-relevant event on {sql_date} with "
            f"GoldsteinScale={goldstein:.2f} and AvgTone={tone:.2f}. "
            f"Actor1={actor_1}; Actor2={actor_2}; EventCode={event_code}."
        )
        return NewsEventItem(
            event_id=f"gdelt_{provider_id}",
            published_at=_iso_from_sql_date(sql_date),
            source="gdelt",
            provider_event_id=provider_id or f"gdelt_{index}",
            title=title,
            summary=summary,
            url=source_url,
            impact_direction=direction,
            impact_score=score,
            confidence=confidence,
            affected_industries=["refining", "shipping", "petrochemicals"],
            tags=_extract_tags(actor_1, actor_2, source_url, extra=[f"EventCode:{event_code}"]),
            llm_model_id="rule-based-gdelt-v1",
            analysis_version="gdelt-rule-v1",
        )

    def _filter_events(
        self,
        items: list[NewsEventItem],
        filters: dict[str, object],
    ) -> list[NewsEventItem]:
        source = filters.get("source")
        if source and source != "all" and source != "gdelt":
            return []

        impact_direction = filters.get("impact_direction")
        if impact_direction:
            items = [item for item in items if item.impact_direction == impact_direction]

        impact_level = filters.get("impact_level")
        if impact_level:
            items = [item for item in items if _matches_impact_level(item.impact_score, str(impact_level))]

        return items


def _infer_gdelt_impact(goldstein: float, tone: float) -> tuple[str, int, float]:
    signal = (goldstein * 0.6) + (tone * 0.4)
    score = min(10, max(0, int(round(abs(signal)))))
    if signal >= 1.5:
        return "bearish", max(score, 4), min(0.85, 0.45 + abs(signal) / 20)
    if signal <= -1.5:
        return "bullish", max(score, 4), min(0.85, 0.45 + abs(signal) / 20)
    return "neutral", min(score, 3), 0.45


def _extract_tags(*values: str, extra: list[str] | None = None) -> list[str]:
    text = " ".join(values).lower()
    tags = [keyword.upper() if keyword in {"opec", "wti"} else keyword.title() for keyword in DEFAULT_GDELT_KEYWORDS if keyword in text]
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


def _row_to_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    if hasattr(row, "items"):
        return dict(row.items())
    return {
        key: getattr(row, key)
        for key in ["SQLDATE", "Actor1Name", "Actor2Name", "EventCode", "GoldsteinScale", "AvgTone", "SOURCEURL"]
        if hasattr(row, key)
    }


def _compact_date(value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    return stripped[:10].replace("-", "")


def _iso_from_sql_date(value: str) -> str:
    if len(value) == 8:
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}T00:00:00Z"
    return _utc_now()


def _escape_sql_like(value: str) -> str:
    safe = "".join(character for character in value if character.isalnum() or character in {" ", "-", "_", "."})
    return safe.replace("'", "''").replace("%", "").replace("_", "")


def _to_non_negative_int(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, 0)


def _to_float(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_str(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


gdelt_event_repository: EventRepository = GDELTProvider()
