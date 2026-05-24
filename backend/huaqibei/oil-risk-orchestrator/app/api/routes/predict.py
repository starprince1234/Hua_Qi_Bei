"""
主预测路由

职责：
    - 接收预测请求
    - 调用 Service 层执行完整推理编排流程
    - 返回标准化 JSON

禁止：
    - 在此文件中写业务逻辑
    - 在此文件中直接调用 pipeline 层
    - 在此文件中实例化 HTTPX
"""

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import Any
import asyncio

from app.schemas.request_schema import PredictRequest, OilDataPoint
from app.schemas.report_schema import (
    APIResponse,
    DataProcessingLog,
    DataProcessingLogV1,
    SelectedFactorsReasonSummary,
    PredictResultPayload,
    PredictionSummaryV1,
    FuturePathBlock,
    FuturePathStep,
    ShockSignal,
    ShockIndustryItem,
    ExplainabilityBlock,
    FactorContributionV1,
    KnowledgeGraphBlock,
    KGPath,
    AIInsightsBlock,
    AIRiskInsight,
    AIIndustryInsight,
    AIKnowledgeGraphInsight,
    AIReportInsight,
    AIFinancingInsight,
    FactorSelectionReasons,
    ReportResult,
)
from app.services.feature_service import FeatureService
from app.services.model_client import ModelClient
from app.services.postprocess_service import PostprocessService
from app.services.risk_service import RiskService
from app.services.industry_service import IndustryService
from app.services.shap_service import ShapService
from app.services.report_service import ReportService
from app.services.ai_insight_service import AIInsightService
from app.services.factor_reason_service import FactorReasonService
from app.services.upload_service import UploadService
from app.schemas.prediction_schema import PredictionResult, PredictionPoint
from app.knowledge_graph.graph_query import GraphQuery
from app.api.dependencies import get_model_client
from app.core.logger import get_logger
from app.utils.json_utils import generate_request_id
from app.core.errors import BusinessError, BusinessErrorCode
from app.core.settings import settings

logger = get_logger(__name__)

router = APIRouter(prefix="/predict", tags=["Prediction"])

# 无状态服务可直接实例化（无依赖注入需求）
_feature_svc = FeatureService()
_post_svc = PostprocessService()
_risk_svc = RiskService()
_industry_svc = IndustryService()
_shap_svc = ShapService()
_report_svc = ReportService()
_ai_insight_svc = AIInsightService()
_factor_reason_svc = FactorReasonService()
_graph_query = GraphQuery()
_upload_svc = UploadService()


def _normalize_kg_level(level: str) -> str:
    text = str(level or "").strip().lower()
    mapping = {
        "critical": "CRITICAL",
        "high": "HIGH",
        "medium": "MEDIUM",
        "low": "LOW",
        "minor": "MINOR",
        "none": "NONE",
        "最严重": "CRITICAL",
        "严重": "HIGH",
        "中": "MEDIUM",
        "较轻微": "LOW",
        "轻微": "MINOR",
        "无": "NONE",
    }
    return mapping.get(text, "MEDIUM")


def _is_oil_ohlc_records(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    first = records[0]
    return "date" in first and "close" in first


def _build_feature_vector_from_snapshot(record: dict[str, Any]) -> tuple[dict[str, float], float]:
    feature_vector: dict[str, float] = {}
    for key, value in record.items():
        if value is None or value == "":
            continue
        try:
            feature_vector[key] = float(value)
        except (TypeError, ValueError):
            continue

    if not feature_vector:
        raise ValueError("宽表因子快照中未找到可用数值特征")

    current_price = (
        feature_vector.get("Brent_Crude(BZ=F)_Close")
        or feature_vector.get("WTI_Crude(CL=F)_Close")
        or feature_vector.get("close")
        or 70.0
    )

    return feature_vector, float(current_price)


def _to_prediction_summary(
    prediction_result: PredictionResult,
) -> PredictionSummaryV1:
    final_point = prediction_result.prediction_path[-1]
    current_price = prediction_result.current_price
    q05 = (final_point.lower_price / current_price) - 1
    q95 = (final_point.upper_price / current_price) - 1

    return PredictionSummaryV1(
        horizon=prediction_result.forecast_horizon,
        return_quantiles={
            "0.05": round(q05, 6),
            "0.5": round(final_point.predicted_return, 6),
            "0.95": round(q95, 6),
        },
        confidence_score=prediction_result.risk_assessment.confidence_score,
        risk_level=prediction_result.risk_assessment.level_display,
        model_version=prediction_result.model_version or "unknown",
    )


def _to_future_path(points: list[PredictionPoint], base_price: float) -> FuturePathBlock:
    steps: list[FuturePathStep] = []
    denominator = max(base_price, 1e-6)
    for point in points:
        steps.append(
            FuturePathStep(
                step=point.step,
                median_price=round(point.predicted_price, 4),
                upper_price=round(point.upper_price, 4),
                lower_price=round(point.lower_price, 4),
                predicted_return=round(point.predicted_return, 6),
                upper_return=round((point.upper_price / denominator) - 1, 6),
                lower_return=round((point.lower_price / denominator) - 1, 6),
            )
        )
    return FuturePathBlock(steps=steps)


def _to_shock_signal(industry_impact) -> ShockSignal:
    impacts = sorted(industry_impact.impacts, key=lambda x: x.impact_magnitude, reverse=True)
    top_items: list[ShockIndustryItem] = []
    for item in impacts:
        top_items.append(
            ShockIndustryItem(
                industry=item.industry,
                direction=item.impact_direction.value,
                magnitude=round(item.impact_magnitude, 4),
            )
        )

    overall_intensity = 0.0
    if industry_impact.impacts:
        overall_intensity = sum(x.impact_magnitude for x in industry_impact.impacts) / len(industry_impact.impacts)

    if overall_intensity >= 0.6:
        alert_level = "HIGH"
    elif overall_intensity >= 0.3:
        alert_level = "MEDIUM"
    else:
        alert_level = "LOW"

    return ShockSignal(
        overall_intensity=round(overall_intensity, 4),
        alert_level=alert_level,
        top_affected_industries=top_items,
    )


def _to_explainability_block(explainability, has_model_shap: bool) -> ExplainabilityBlock:
    factors: list[FactorContributionV1] = []
    for item in explainability.top_factors:
        factors.append(
            FactorContributionV1(
                factor=item.factor_name,
                contribution=item.shap_value,
            )
        )
    method = "shap_or_proxy" if has_model_shap else "proxy"
    return ExplainabilityBlock(top_factors=factors, method=method)


def _to_knowledge_graph_block(
    industries: list[str],
    node_levels_map: dict[str, dict[str, str]] | None = None,
) -> KnowledgeGraphBlock:
    alias = {
        "refinery": "chemical",
        "logistics": "shipping",
        "heavy_manufacturing": "manufacturing",
    }
    paths: list[KGPath] = []
    for industry in industries:
        mapped = alias.get(industry, industry)
        path_nodes = _graph_query.get_path(mapped)
        if not path_nodes:
            continue
        labels = _graph_query.get_path_labels(mapped)
        mapped_levels = node_levels_map.get(industry, {}) if node_levels_map else {}
        paths.append(
            KGPath(
                industry=industry,
                path_nodes=path_nodes,
                path_labels=labels,
                arrow_path=" → ".join(labels),
                node_levels=[
                    {
                        "name": label,
                        "level": _normalize_kg_level(mapped_levels.get(label, "MEDIUM")),
                    }
                    for label in labels
                ],
            )
        )
    return KnowledgeGraphBlock(paths=paths)


@router.post(
    "",
    include_in_schema=True,
    response_model=APIResponse,
    summary="油价风险智能预测",
    description="完整推理编排接口：特征工程 → 云端模型 → 后处理 → 解释 → 报告",
    responses={
        400: {"model": APIResponse},
        422: {"model": APIResponse},
        503: {"model": APIResponse},
        500: {"model": APIResponse},
    },
)
async def predict(
    request: PredictRequest,
    model_client: ModelClient = Depends(get_model_client),
) -> JSONResponse:
    """
    主预测端点。

    完整数据流：
        用户数据 → 特征工程 → as-of对齐 → 远程模型调用
        → 路径还原 → 风险分级 → 行业冲击映射
        → SHAP解释 → 知识图谱增强 → LLM报告生成 → 返回前端

    Args:
        request: 预测请求体（含油价序列、宏观因子、预测配置）。
        model_client: 注入的模型客户端（支持 mock/real 切换）。

    Returns:
        APIResponse 包装的 RiskReport JSON。
    """
    request_id = generate_request_id()
    feature_result: dict[str, Any] | None = None
    if request.oil_data is None and request.file_id:
        cached_rows = _upload_svc.get_records_by_file_id(request.file_id)
        if not cached_rows:
            raise BusinessError(
                code=BusinessErrorCode.VALIDATION_ERROR,
                message="file_id 无效或已过期",
                status_code=400,
            )
        if _is_oil_ohlc_records(cached_rows):
            request.oil_data = [OilDataPoint(**row) for row in cached_rows]
        else:
            feature_vector, current_price = _build_feature_vector_from_snapshot(cached_rows[0])
            feature_result = {
                "feature_vector": feature_vector,
                "current_price": current_price,
                "row_count": len(cached_rows),
                "missing_ratio": 0.0,
                "repair_log": [],
            }

    if not request.oil_data and feature_result is None:
        raise BusinessError(
            code=BusinessErrorCode.VALIDATION_ERROR,
            message="oil_data 不能为空",
            status_code=400,
        )

    logger.info(
        f"[{request_id}] 收到预测请求 rows={len(request.oil_data or [])} "
        f"mode={'snapshot' if feature_result is not None else 'timeseries'}"
    )

    # ─── Step 1: 特征工程 ───────────────────────────────────────────
    if feature_result is None:
        try:
            feature_result = _feature_svc.build_feature_matrix(request)
        except ValueError as e:
            logger.warning(f"[{request_id}] 特征工程失败: {e}")
            raise BusinessError(
                code=BusinessErrorCode.VALIDATION_ERROR,
                message=str(e),
                status_code=400,
            )

    feature_vector = feature_result["feature_vector"]
    current_price = feature_result["current_price"]
    repair_log = feature_result.get("repair_log", [])

    # ─── Step 2: 远程模型调用 ───────────────────────────────────────
    try:
        model_response = await model_client.predict(
            feature_vector=feature_vector,
            forecast_horizon=request.horizon,
            include_shap=request.include_explainability,
            current_price=current_price,
        )
    except RuntimeError as e:
        logger.error(f"[{request_id}] 模型调用失败: {e}")
        raise BusinessError(
            code=BusinessErrorCode.MODEL_UNAVAILABLE,
            message=f"云端模型服务暂不可用: {e}",
            status_code=503,
        )

    # ─── Step 3: 路径还原 ───────────────────────────────────────────
    prediction_path = _post_svc.restore_prediction_path(model_response, current_price)

    # ─── Step 4: 风险分级 ───────────────────────────────────────────
    risk_assessment = _risk_svc.assess_risk(model_response)

    prediction_result = PredictionResult(
        current_price=round(current_price, 4),
        forecast_horizon=request.horizon,
        prediction_path=prediction_path,
        risk_assessment=risk_assessment,
        model_version=model_response.model_version,
    )

    # ─── Step 5: 行业冲击映射 ───────────────────────────────────────
    industry_impact = await _industry_svc.analyze_impact(
        model_response,
        target_industries=request.industries,
    )

    competition_path = _post_svc.build_competition_multi_path(
        model_response=model_response,
        current_price=current_price,
        full_path=prediction_path,
    )

    knowledge_graph_path = [
        {
            "industry": imp.industry,
            "path_nodes": _graph_query.get_path(imp.industry),
            "path_labels": _graph_query.get_path_labels(imp.industry),
        }
        for imp in industry_impact.impacts
        if _graph_query.get_path(imp.industry)
    ]

    # ─── Step 6: SHAP 解释 ──────────────────────────────────────────
    explainability = _shap_svc.build_explainability(model_response)
    top_factor_names = [item.factor_name for item in explainability.top_factors]
    reason_summary = _factor_reason_svc.build_summary(top_factor_names)
    factor_selection_reasons = _factor_reason_svc.build_factor_selection_reasons(top_factor_names)

    # ─── Step 7: 并发 LLM 生成（4 模块） ─────────────────────────────
    risk_task = _ai_insight_svc.build_risk_insight(prediction_result)
    industry_task = _ai_insight_svc.build_industry_insight(prediction_result, industry_impact)
    kg_task = _ai_insight_svc.build_kg_insight(prediction_result, knowledge_graph_path)
    report_task = _report_svc.generate_report(
        prediction=prediction_result,
        industry_impact=industry_impact,
        explainability=explainability,
        template=request.report_style,
        data_processing_log=DataProcessingLog(
            validation_summary={
                "row_count": feature_result.get("row_count", 0),
                "missing_ratio": feature_result.get("missing_ratio", 0.0),
            },
            repairs=repair_log,
            asof_alignment={"enabled": bool(request.macro_factors), "dropped_rows": 0, "reason": ""},
        ),
        selected_factors_reason_summary=SelectedFactorsReasonSummary(**reason_summary),
        knowledge_graph_path=knowledge_graph_path,
        model_id=settings.LLM_MODEL_REPORT_SUMMARY,
        system_prompt=settings.LLM_SYSTEM_PROMPT_REPORT_SUMMARY,
    )

    financing_task = _ai_insight_svc.build_financing_insight(
        prediction=prediction_result,
        industries=request.industries or [],
        top_factors=[
            {
                "factor_name": item.factor_name,
                "contribution": item.shap_value,
                "direction": item.direction,
            }
            for item in explainability.top_factors[:10]
        ],
    )

    risk_insight, industry_insight, kg_result, report, financing_insight = await asyncio.gather(
        risk_task,
        industry_task,
        kg_task,
        report_task,
        financing_task,
    )
    kg_insight, kg_node_levels = kg_result

    report_result: ReportResult = _report_svc.to_report_result(report)

    payload = PredictResultPayload(
        prediction=_to_prediction_summary(prediction_result),
        future_path=_to_future_path(competition_path, prediction_result.current_price),
        shock_signal=_to_shock_signal(industry_impact),
        explainability=_to_explainability_block(
            explainability,
            has_model_shap=bool(model_response.shap_values and model_response.shap_values.values),
        ),
        knowledge_graph=(
            _to_knowledge_graph_block(
                [item.industry for item in industry_impact.impacts],
                node_levels_map=kg_node_levels,
            )
            if request.include_knowledge_graph
            else _to_knowledge_graph_block([], {})
        ),
        ai_insights=AIInsightsBlock(
            risk=AIRiskInsight(
                risk_level=risk_insight.risk_level,
                detail=risk_insight.detail,
                model_id=risk_insight.model_id,
            ),
            industry=AIIndustryInsight(
                detail=industry_insight.detail,
                model_id=industry_insight.model_id,
            ),
            knowledge_graph=AIKnowledgeGraphInsight(
                detail=kg_insight.detail,
                model_id=kg_insight.model_id,
            ),
            report=AIReportInsight(
                detail=report.executive_summary + "\n\n" + report.detailed_analysis + "\n\n" + report.risk_advice,
                model_id=settings.LLM_MODEL_REPORT_SUMMARY,
            ),
            financing=AIFinancingInsight(
                detail=financing_insight.detail,
                model_id=financing_insight.model_id,
            ),
        ),
        factor_selection_reasons=FactorSelectionReasons(**factor_selection_reasons),
        report=report_result,
        data_processing_log=DataProcessingLogV1(
            validation_passed=True,
            repair_actions=[item.model_dump() if hasattr(item, "model_dump") else item for item in repair_log],
            asof_alignment=bool(request.macro_factors),
            lag_features_built=True,
        ),
    )

    logger.info(f"[{request_id}] 预测完成 risk={risk_assessment.level.value}")

    response = APIResponse.ok(data=payload.model_dump())
    response.request_id = request_id

    return JSONResponse(content=response.model_dump())
