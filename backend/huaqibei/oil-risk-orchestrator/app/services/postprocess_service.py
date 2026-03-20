from __future__ import annotations

from app.schemas.model_response_schema import ModelPredictResponse
from app.schemas.prediction_schema import PredictionResponse, FactorContribution, IndustryImpactResult
from app.services.shap_service import parse_shap
from app.services.risk_service import compute_risk
from app.services.industry_service import compute_industry_impacts
from app.core.logger import get_logger

logger = get_logger(__name__)


async def postprocess(
    raw_response: ModelPredictResponse,
    horizon: int,
    industries: list[str],
    file_id: str = "",
    report_style: str = "general",
    include_shap: bool = True,
) -> PredictionResponse:
    """Convert a raw ModelPredictResponse into the final PredictionResponse."""
    factor_contributions: list[FactorContribution] = []
    if include_shap and raw_response.shap_values and raw_response.feature_names:
        factor_contributions = parse_shap(raw_response.shap_values, raw_response.feature_names)

    risk_metrics = compute_risk(raw_response.quantiles, horizon)

    price_change_pct = 0.0
    if raw_response.predictions and len(raw_response.predictions) > 1:
        p0 = raw_response.predictions[0]
        pn = raw_response.predictions[-1]
        price_change_pct = (pn - p0) / max(abs(p0), 1e-9)

    industry_impacts = compute_industry_impacts(price_change_pct, industries, horizon) if industries else []

    return PredictionResponse(
        file_id=file_id,
        horizon=horizon,
        predictions=raw_response.predictions,
        quantiles=raw_response.quantiles,
        risk_level=risk_metrics["risk_level"],
        var_95=risk_metrics["var_95"],
        cvar_95=risk_metrics["cvar_95"],
        volatility=risk_metrics["volatility"],
        factor_contributions=factor_contributions,
        industry_impacts=industry_impacts,
        ai_insight="",
        report_style=report_style,
    )
