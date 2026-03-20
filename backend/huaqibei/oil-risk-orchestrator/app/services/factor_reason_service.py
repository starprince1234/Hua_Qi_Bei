"""
因子原因服务

职责：
    - 从 selected_factor_reasons.json 加载预置的因子驱动原因
    - 根据 SHAP Top 特征匹配对应解释
"""

import json
import os
from typing import Any

from app.core.constants import MAX_FACTOR_REASONS_DISPLAY
from app.core.logger import get_logger

logger = get_logger(__name__)

_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "selected_factor_reasons.json"
)


def _load_reasons() -> dict[str, Any]:
    """加载因子原因字典。"""
    try:
        path = os.path.abspath(_DATA_PATH)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"因子原因数据加载失败: {e}，返回空字典")
        return {}


class FactorReasonService:
    """
    因子驱动原因服务。

    根据 SHAP Top 特征，从预置字典中检索可读解释。
    """

    def __init__(self) -> None:
        self._reasons: dict[str, Any] = _load_reasons()

    def get_reasons(
        self,
        top_features: list[dict[str, Any]],
        predicted_return: float,
        max_results: int = MAX_FACTOR_REASONS_DISPLAY,
    ) -> list[dict[str, Any]]:
        """
        获取 Top 特征的驱动原因解释。

        Args:
            top_features: SHAP 贡献特征列表（含 feature / shap_value / direction）。
            predicted_return: 预测收益率（用于方向过滤）。
            max_results: 最大返回数量。

        Returns:
            [{"feature": str, "reason": str, "direction": str, "shap_value": float}, ...]
        """
        result: list[dict[str, Any]] = []

        for feat_item in top_features[:max_results]:
            feature = str(feat_item.get("feature", ""))
            direction = str(feat_item.get("direction", ""))
            shap_value = float(feat_item.get("shap_value", 0.0))

            reason_entry = self._reasons.get(feature)
            if reason_entry:
                if isinstance(reason_entry, dict):
                    reason = reason_entry.get(direction, reason_entry.get("default", str(reason_entry)))
                else:
                    reason = str(reason_entry)
            else:
                reason = self._build_fallback_reason(
                    feature=feature,
                    shap_value=shap_value,
                    predicted_return=predicted_return,
                )

            result.append(
                {
                    "feature": feature,
                    "reason": reason,
                    "direction": direction,
                    "shap_value": shap_value,
                }
            )

        return result

    def _build_fallback_reason(
        self,
        feature: str,
        shap_value: float,
        predicted_return: float,
    ) -> str:
        direction_word = "上涨" if predicted_return >= 0 else "下跌"
        influence = "正向推动" if shap_value >= 0 else "负向压制"
        return f"{feature} 对本次油价{direction_word}预测产生了{influence}（贡献值 {shap_value:+.4f}）。"
