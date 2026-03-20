from __future__ import annotations

import json
from pathlib import Path
from functools import lru_cache

from app.schemas.prediction_schema import FactorContribution
from app.core.logger import get_logger

logger = get_logger(__name__)

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "selected_factor_reasons.json"


@lru_cache(maxsize=1)
def _load_reasons() -> dict:
    if _DATA_PATH.exists():
        return json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    logger.warning("selected_factor_reasons.json not found", extra={"path": str(_DATA_PATH)})
    return {}


def get_factor_reasons(contributions: list[FactorContribution]) -> list[FactorContribution]:
    """Enrich FactorContribution objects with human-readable reason strings."""
    reasons = _load_reasons()
    enriched = []
    for fc in contributions:
        template = reasons.get(fc.feature, {})
        key = "positive" if fc.direction == "up" else "negative"
        fc = fc.model_copy(update={"reason": template.get(key, "")})
        enriched.append(fc)
    return enriched
