from __future__ import annotations

from app.core.constants import INDUSTRY_SENSITIVITY
from app.knowledge_graph.graph_query import get_transmission_path, get_affected_industries

_INDUSTRY_LABELS: dict[str, str] = {
    "aviation": "航空业",
    "shipping": "航运业",
    "chemical": "化工业",
}

_PATH_LABELS: dict[str, str] = {
    "crude_oil": "国际原油",
    "brent": "布伦特原油",
    "wti": "WTI原油",
    "refinery": "炼油环节",
    "opec": "OPEC",
    "geopolitics": "地缘政治",
    "supply": "全球供应",
    "demand": "全球需求",
    "usd": "美元指数",
    "financial_mkt": "金融市场",
    "natural_gas": "天然气",
    "renewable": "可再生能源",
}


def map_transmission(
    price_change_pct: float,
    horizon: int,
    industries: list[str],
) -> dict[str, dict]:
    """
    Map an oil price change to downstream industry impacts using the knowledge graph.

    Returns:
        Dict keyed by industry with impact details including transmission path.
    """
    result: dict[str, dict] = {}
    for industry in industries:
        sensitivity = INDUSTRY_SENSITIVITY.get(industry, 0.3)
        impact = price_change_pct * sensitivity / (1 + horizon / 30)
        impact = max(-1.0, min(1.0, impact))

        path = get_transmission_path("crude_oil", industry)
        path_labels = [_PATH_LABELS.get(n, n) for n in path]

        result[industry] = {
            "label": _INDUSTRY_LABELS.get(industry, industry),
            "impact_score": round(impact, 4),
            "direction": "up" if impact > 0.01 else ("down" if impact < -0.01 else "neutral"),
            "transmission_path": path,
            "transmission_path_labels": path_labels,
            "sensitivity": sensitivity,
        }
    return result
