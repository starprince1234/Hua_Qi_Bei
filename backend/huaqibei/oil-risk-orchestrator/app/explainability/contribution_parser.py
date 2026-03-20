from __future__ import annotations

from typing import Literal


def parse_shap_contributions(
    shap_values: list[list[float]],
    feature_names: list[str],
) -> list[dict]:
    """
    Aggregate SHAP values across samples and return per-feature importance.

    Args:
        shap_values: 2-D list [samples × features].
        feature_names: Feature names matching the columns of shap_values.

    Returns:
        List of dicts sorted by |mean SHAP value| descending:
        [{"feature": str, "value": float, "direction": "up"|"down"|"neutral"}, ...]
    """
    if not shap_values or not feature_names:
        return []

    n_features = len(feature_names)
    mean_shap: list[float] = []
    for fi in range(n_features):
        col_values = [row[fi] for row in shap_values if fi < len(row)]
        mean_shap.append(sum(col_values) / len(col_values) if col_values else 0.0)

    contributions = []
    for name, value in zip(feature_names, mean_shap):
        if value > 0.01:
            direction: Literal["up", "down", "neutral"] = "up"
        elif value < -0.01:
            direction = "down"
        else:
            direction = "neutral"
        contributions.append({"feature": name, "value": round(value, 6), "direction": direction})

    contributions.sort(key=lambda x: abs(x["value"]), reverse=True)
    return contributions
