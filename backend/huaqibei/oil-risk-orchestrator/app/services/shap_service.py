"""
SHAP 归因服务：解析模型服务返回的 SHAP 值，转换为结构化贡献列表
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..schemas.report_schema import ShapContribution


def parse_shap_values(
    raw_response: Dict[str, Any],
    features: Dict[str, float],
) -> Optional[List[ShapContribution]]:
    """
    从模型服务响应中提取并解析 SHAP 值。

    Parameters
    ----------
    raw_response:
        模型服务 /predict/returns 的原始 JSON 响应体。
    features:
        本次推理所使用的特征名称到数值的映射。

    Returns
    -------
    List[ShapContribution] 或 None（若响应中不含 SHAP 数据）。
    """
    shap_raw: Optional[Dict[str, float]] = raw_response.get("shap_values")
    if shap_raw is None:
        return None

    contributions: List[ShapContribution] = []
    for feature_name, shap_val in shap_raw.items():
        contributions.append(
            ShapContribution(
                feature=feature_name,
                shap_value=float(shap_val),
                feature_value=float(features.get(feature_name, 0.0)),
            )
        )

    # 按 SHAP 绝对值降序排列，便于展示最重要因子
    contributions.sort(key=lambda c: abs(c.shap_value), reverse=True)
    return contributions


def top_shap_features(contributions: List[ShapContribution], top_n: int = 5) -> List[ShapContribution]:
    """返回绝对贡献值最大的前 top_n 个特征。"""
    return contributions[:top_n]
