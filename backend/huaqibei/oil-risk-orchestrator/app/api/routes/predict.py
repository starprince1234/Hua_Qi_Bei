from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies import verify_api_key
from app.schemas.request_schema import PredictRequest
from app.schemas.prediction_schema import PredictionResponse
from app.services.feature_service import load_and_preprocess
from app.services.model_client import call_model
from app.services.shap_service import parse_shap
from app.services.risk_service import compute_risk
from app.services.factor_reason_service import get_factor_reasons
from app.services.ai_insight_service import generate_insight
from app.services.industry_service import compute_industry_impacts
from app.core.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["predict"])


@router.post("/predict", response_model=PredictionResponse, summary="Oil price prediction")
async def predict(
    req: PredictRequest,
    _: None = Depends(verify_api_key),
) -> PredictionResponse:
    logger.info("Predict request received", extra={"file_id": req.file_id, "horizon": req.horizon})

    # 1. Feature engineering
    features_df = await load_and_preprocess(req.file_id)

    # 2. Call model service
    model_resp = await call_model(features_df, req.horizon, include_shap=req.include_explainability)

    # 3. SHAP / factor contributions
    factor_contributions = []
    if req.include_explainability and model_resp.shap_values:
        factor_contributions = parse_shap(model_resp.shap_values, model_resp.feature_names or [])
        factor_contributions = get_factor_reasons(factor_contributions)

    # 4. Risk metrics
    risk_metrics = compute_risk(model_resp.quantiles, req.horizon)

    # 5. Industry impacts
    industry_impacts = []
    if req.industries:
        price_change_pct = (
            (model_resp.predictions[-1] - model_resp.predictions[0]) / max(abs(model_resp.predictions[0]), 1e-9)
            if model_resp.predictions else 0.0
        )
        industry_impacts = compute_industry_impacts(price_change_pct, req.industries, req.horizon)

    # 6. AI insight
    ai_insight = await generate_insight(
        predictions=model_resp.predictions,
        risk_metrics=risk_metrics,
        factor_contributions=factor_contributions,
        horizon=req.horizon,
    )

    return PredictionResponse(
        file_id=req.file_id,
        horizon=req.horizon,
        predictions=model_resp.predictions,
        quantiles=model_resp.quantiles,
        risk_level=risk_metrics["risk_level"],
        var_95=risk_metrics["var_95"],
        cvar_95=risk_metrics["cvar_95"],
        volatility=risk_metrics["volatility"],
        factor_contributions=factor_contributions,
        industry_impacts=industry_impacts,
        ai_insight=ai_insight,
        report_style=req.report_style,
    )
