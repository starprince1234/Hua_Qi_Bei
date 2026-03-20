"""
预测接口路由
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_feature_service,
    get_model_client,
    get_postprocess_service,
    get_risk_service,
    get_shap_service,
)
from app.core.logger import get_logger
from app.schemas.request_schema import PredictRequest
from app.services.feature_service import FeatureService
from app.services.model_client import ModelClient
from app.services.postprocess_service import PostprocessService
from app.services.risk_service import RiskService
from app.services.shap_service import ShapService

logger = get_logger(__name__)
router = APIRouter(prefix="/predict", tags=["predict"])


@router.post("", summary="预测油价风险")
async def predict(
    request: PredictRequest,
    feature_svc: FeatureService = Depends(get_feature_service),
    model_client: ModelClient = Depends(get_model_client),
    risk_svc: RiskService = Depends(get_risk_service),
    shap_svc: ShapService = Depends(get_shap_service),
    postprocess_svc: PostprocessService = Depends(get_postprocess_service),
) -> dict:
    records = [r.model_dump() for r in request.data]

    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="数据不能为空",
        )

    current_price = float(records[-1].get("close") or 80.0)

    # 特征工程
    feature_vector = feature_svc.build_feature_vector(
        records=records,
        forecast_horizon=request.forecast_horizon,
    )

    # 调用模型
    if request.mock_mode:
        model_response = await model_client.mock_predict(
            feature_vector=feature_vector,
            forecast_horizon=request.forecast_horizon,
            include_shap=request.include_shap,
            current_price=current_price,
        )
    else:
        model_response = await model_client.predict(
            feature_vector=feature_vector,
            forecast_horizon=request.forecast_horizon,
            include_shap=request.include_shap,
        )

    # SHAP 处理
    shap_contributions, _ = shap_svc.process(
        shap_values=model_response.shap_values,
        predicted_return=model_response.median,
        forecast_horizon=request.forecast_horizon,
    )

    # 构建预测结果
    prediction = risk_svc.build_prediction_result(
        model_response=model_response,
        current_price=current_price,
        forecast_horizon=request.forecast_horizon,
        shap_top_features=shap_contributions,
    )

    prediction = postprocess_svc.postprocess(prediction)

    logger.info(
        f"predict: horizon={request.forecast_horizon} "
        f"level={prediction.risk_assessment.level.value}"
    )
    return prediction.model_dump(mode="json")
