from __future__ import annotations

from app.schemas.prediction_schema import FactorContribution
from app.explainability.contribution_parser import parse_shap_contributions
from app.explainability.factor_dictionary import FACTOR_DICT
from app.core.logger import get_logger

logger = get_logger(__name__)


def parse_shap(
    shap_values: list[list[float]],
    feature_names: list[str],
) -> list[FactorContribution]:
    """Convert raw SHAP matrix into sorted FactorContribution objects."""
    raw = parse_shap_contributions(shap_values, feature_names)

    contributions: list[FactorContribution] = []
    for item in raw:
        meta = FACTOR_DICT.get(item["feature"], {})
        contributions.append(
            FactorContribution(
                feature=item["feature"],
                value=item["value"],
                direction=item["direction"],
                label=meta.get("label", item["feature"]),
                category=meta.get("category", "其他因素"),
            )
        )
    return contributions
