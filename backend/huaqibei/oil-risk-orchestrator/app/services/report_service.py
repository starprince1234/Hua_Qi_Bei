"""
报告生成服务：将各子服务的输出组装为完整的预测报告
"""
from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from ..schemas.report_schema import HorizonReport, PredictionReport, QuantilePrediction
from ..schemas.request_schema import Horizon
from . import (
    ai_insight_service,
    factor_reason_service,
    model_client,
    postprocess_service,
    risk_service,
    shap_service,
)


def build_horizon_report(
    features: Dict[str, float],
    horizon: Horizon,
    include_shap: bool = False,
    request_id: Optional[str] = None,
) -> HorizonReport:
    """
    为单一时间窗口生成预测报告。

    Parameters
    ----------
    features:
        预处理后的特征字典。
    horizon:
        预测时间窗口枚举值。
    include_shap:
        是否请求 SHAP 归因。
    request_id:
        可选请求追踪 ID。

    Returns
    -------
    HorizonReport
    """
    raw = model_client.predict(
        features=features,
        horizon=horizon.value,
        include_shap=include_shap,
        request_id=request_id,
    )

    q10, q50, q90 = postprocess_service.extract_quantiles(raw)
    q10, q50, q90 = postprocess_service.normalize_quantiles(q10, q50, q90)

    risk_level, risk_score = risk_service.assess_risk(q10, q50, q90, horizon.value)

    shap_contributions = None
    factor_reasons: List[str] = []
    if include_shap:
        shap_contributions = shap_service.parse_shap_values(raw, features)
        if shap_contributions:
            factor_reasons = factor_reason_service.generate_factor_reasons(shap_contributions)

    ai_insight = ai_insight_service.generate_insight(
        horizon=horizon.value,
        q10=q10,
        q50=q50,
        q90=q90,
        risk_level=risk_level,
        factor_reasons=factor_reasons,
    )

    return HorizonReport(
        horizon=horizon,
        prediction=QuantilePrediction(q10=q10, q50=q50, q90=q90),
        risk_level=risk_level,
        risk_score=risk_score,
        ai_insight=ai_insight,
        factor_reasons=factor_reasons,
        shap_contributions=shap_contributions,
    )


def build_full_report(
    features: Dict[str, float],
    horizons: List[Horizon],
    include_shap: bool = False,
    upload_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> PredictionReport:
    """
    为多个时间窗口生成完整预测报告。

    Parameters
    ----------
    features:
        预处理后的特征字典。
    horizons:
        需要预测的时间窗口列表。
    include_shap:
        是否请求 SHAP 归因。
    upload_id:
        关联的数据上传标识符（可选）。
    request_id:
        可选请求追踪 ID。

    Returns
    -------
    PredictionReport
    """
    horizon_reports = [
        build_horizon_report(features, h, include_shap, request_id)
        for h in horizons
    ]

    risk_levels = [r.risk_level for r in horizon_reports]
    highest_risk = max(risk_levels, key=lambda rl: ["low", "medium", "high", "extreme"].index(rl))
    summary = f"综合分析 {len(horizons)} 个预测窗口，最高风险等级为 {highest_risk}。"

    return PredictionReport(
        report_id=str(uuid.uuid4()),
        upload_id=upload_id,
        horizons=horizon_reports,
        summary=summary,
    )
