from __future__ import annotations

_RISK_ZH = {"low": "低", "medium": "中等", "high": "高", "extreme": "极高"}
_DIRECTION_ZH = {"up": "上行", "down": "下行", "neutral": "震荡"}


def build_narrative(
    contributions: list[dict],
    horizon: int,
    risk_level: str,
    language: str = "zh",
) -> str:
    """
    Construct a plain-language narrative from factor contributions.

    Args:
        contributions: List of dicts with keys: feature, label, value, direction, reason.
        horizon: Prediction horizon in days.
        risk_level: "low" | "medium" | "high" | "extreme".
        language: Currently only "zh" (Chinese) is supported.

    Returns:
        Multi-sentence narrative string.
    """
    risk_zh = _RISK_ZH.get(risk_level, "中等")

    up_factors = [c for c in contributions if c.get("direction") == "up"]
    down_factors = [c for c in contributions if c.get("direction") == "down"]

    def _labels(factors: list[dict], n: int = 3) -> str:
        return "、".join(c.get("label", c.get("feature", "")) for c in factors[:n])

    parts: list[str] = [
        f"模型综合评估显示，未来{horizon}天油价整体风险等级为{risk_zh}。"
    ]

    if up_factors:
        parts.append(f"支撑油价上行的核心因素包括：{_labels(up_factors)}，" + up_factors[0].get("reason", "") + "。")

    if down_factors:
        parts.append(f"对油价形成压制的主要因素为：{_labels(down_factors)}，" + down_factors[0].get("reason", "") + "。")

    if not up_factors and not down_factors:
        parts.append("当前各类驱动因素影响相对均衡，油价短期内或维持区间震荡格局。")

    parts.append("建议结合自身业务敞口，制定相应风险对冲策略。")
    return "".join(parts)
