"""
报告生成接口路由
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_ai_insight_service,
    get_factor_reason_service,
    get_feature_service,
    get_industry_service,
    get_model_client,
    get_postprocess_service,
    get_report_service,
    get_risk_service,
    get_shap_service,
    get_upload_service,
)
from app.core.logger import get_logger
from app.schemas.request_schema import ReportRequest
from app.services.ai_insight_service import AIInsightService
from app.services.factor_reason_service import FactorReasonService
from app.services.feature_service import FeatureService
from app.services.industry_service import IndustryService
from app.services.model_client import ModelClient
from app.services.postprocess_service import PostprocessService
from app.services.report_service import ReportService
from app.services.risk_service import RiskService
from app.services.shap_service import ShapService
from app.services.upload_service import UploadService

logger = get_logger(__name__)
router = APIRouter(prefix="/report", tags=["report"])


@router.post("", summary="生成完整风险报告")
async def generate_report(
    request: ReportRequest,
    feature_svc: FeatureService = Depends(get_feature_service),
    model_client: ModelClient = Depends(get_model_client),
    risk_svc: RiskService = Depends(get_risk_service),
    shap_svc: ShapService = Depends(get_shap_service),
    postprocess_svc: PostprocessService = Depends(get_postprocess_service),
    industry_svc: IndustryService = Depends(get_industry_service),
    report_svc: ReportService = Depends(get_report_service),
    ai_svc: AIInsightService = Depends(get_ai_insight_service),
    factor_svc: FactorReasonService = Depends(get_factor_reason_service),
    upload_svc: UploadService = Depends(get_upload_service),
) -> dict:
    # 获取数据来源
    if request.prediction_id:
        records = upload_svc.get_records(request.prediction_id)
        if not records:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"上传 ID {request.prediction_id} 不存在或已过期",
            )
    elif request.data:
        records = [r.model_dump() for r in request.data]
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要提供 prediction_id 或 data",
        )

    current_price = float(records[-1].get("close") or 80.0)

    feature_vector = feature_svc.build_feature_vector(
        records=records,
        forecast_horizon=request.forecast_horizon,
    )

    if request.mock_mode:
        model_response = await model_client.mock_predict(
            feature_vector=feature_vector,
            forecast_horizon=request.forecast_horizon,
        )
    else:
        model_response = await model_client.predict(
            feature_vector=feature_vector,
            forecast_horizon=request.forecast_horizon,
        )

    shap_contributions, _ = shap_svc.process(
        shap_values=model_response.shap_values,
        predicted_return=model_response.median,
        forecast_horizon=request.forecast_horizon,
    )

    prediction = risk_svc.build_prediction_result(
        model_response=model_response,
        current_price=current_price,
        forecast_horizon=request.forecast_horizon,
        shap_top_features=shap_contributions,
    )
    prediction = postprocess_svc.postprocess(prediction)

    industry_impact = industry_svc.analyze(prediction=prediction)
    factor_reasons = factor_svc.get_reasons(
        top_features=shap_contributions,
        predicted_return=model_response.median,
    )

    # AI 解释（并发）
    import asyncio

    ai_risk, ai_industry, (ai_kg, node_levels) = await asyncio.gather(
        ai_svc.build_risk_insight(prediction),
        ai_svc.build_industry_insight(prediction, industry_impact),
        ai_svc.build_kg_insight(
            prediction,
            [{"industry": i.industry, "path_labels": []} for i in industry_impact.impacts],
        ),
    )

    report = await report_svc.build_report(
        prediction=prediction,
        industry_impact=industry_impact,
        factor_reasons=factor_reasons,
        ai_risk_insight=ai_risk,
        ai_industry_insight=ai_industry,
        ai_kg_insight=ai_kg,
        node_levels=node_levels,
        report_format=request.report_format,
    )

    if request.report_format == "markdown":
        return {"markdown": report_svc.to_markdown(report), "report_id": report.report_id}

    logger.info(f"report: report_id={report.report_id}")
    return report.model_dump(mode="json")
