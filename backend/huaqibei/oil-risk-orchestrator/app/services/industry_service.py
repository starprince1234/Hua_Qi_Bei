from __future__ import annotations

from app.core.constants import INDUSTRY_SENSITIVITY
from app.schemas.prediction_schema import IndustryImpactResult
from app.core.logger import get_logger

logger = get_logger(__name__)

_INDUSTRY_LABELS: dict[str, str] = {
    "aviation": "航空",
    "shipping": "航运",
    "chemical": "化工",
}

_DIRECTION_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "aviation": {
        "up": "油价上涨将推高航空燃油成本，压缩航空公司利润空间，可能引发机票涨价。",
        "down": "油价下跌将降低航空燃油成本，改善航空公司盈利能力，利好行业扩张。",
    },
    "shipping": {
        "up": "油价上涨导致船用燃油成本上升，运费附加费可能随之提高。",
        "down": "油价下跌降低船用燃油支出，有助于降低航运综合成本。",
    },
    "chemical": {
        "up": "油价上涨推升石化原料价格，化工企业原材料成本大幅增加。",
        "down": "油价下跌降低石化原料价格，有利于化工产品毛利率改善。",
    },
}


def compute_industry_impacts(
    price_change_pct: float,
    industries: list[str],
    horizon: int,
) -> list[IndustryImpactResult]:
    """Estimate industry-level cost impacts from an expected price change."""
    impacts: list[IndustryImpactResult] = []
    horizon_discount = 1.0 / (1 + horizon / 30)  # shorter horizon → stronger near-term effect

    for ind in industries:
        if ind not in INDUSTRY_SENSITIVITY:
            continue
        sensitivity = INDUSTRY_SENSITIVITY[ind]
        raw_score = price_change_pct * sensitivity * horizon_discount
        raw_score = max(-1.0, min(1.0, raw_score))

        if abs(raw_score) < 0.01:
            direction = "neutral"
        elif raw_score > 0:
            direction = "up"
        else:
            direction = "down"

        confidence = min(0.95, 0.5 + abs(raw_score) * 2)
        desc_map = _DIRECTION_DESCRIPTIONS.get(ind, {})
        description = desc_map.get("up" if direction == "up" else "down", "")

        impacts.append(
            IndustryImpactResult(
                industry=ind,
                impact_score=round(raw_score, 4),
                direction=direction,
                confidence=round(confidence, 4),
                description=description,
            )
        )
    return impacts
