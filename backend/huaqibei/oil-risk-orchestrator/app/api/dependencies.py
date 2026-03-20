"""
FastAPI 依赖注入

提供可复用的依赖项，如服务实例单例注入。
"""

from functools import lru_cache

from app.services.feature_service import FeatureService
from app.services.risk_service import RiskService
from app.services.postprocess_service import PostprocessService
from app.services.industry_service import IndustryService
from app.services.report_service import ReportService
from app.services.shap_service import ShapService
from app.services.upload_service import UploadService
from app.services.ai_insight_service import AIInsightService
from app.services.factor_reason_service import FactorReasonService
from app.services.model_client import ModelClient


@lru_cache(maxsize=1)
def get_feature_service() -> FeatureService:
    return FeatureService()


@lru_cache(maxsize=1)
def get_risk_service() -> RiskService:
    return RiskService()


@lru_cache(maxsize=1)
def get_postprocess_service() -> PostprocessService:
    return PostprocessService()


@lru_cache(maxsize=1)
def get_industry_service() -> IndustryService:
    return IndustryService()


@lru_cache(maxsize=1)
def get_report_service() -> ReportService:
    return ReportService()


@lru_cache(maxsize=1)
def get_shap_service() -> ShapService:
    return ShapService()


@lru_cache(maxsize=1)
def get_upload_service() -> UploadService:
    return UploadService()


@lru_cache(maxsize=1)
def get_ai_insight_service() -> AIInsightService:
    return AIInsightService()


@lru_cache(maxsize=1)
def get_factor_reason_service() -> FactorReasonService:
    return FactorReasonService()


@lru_cache(maxsize=1)
def get_model_client() -> ModelClient:
    return ModelClient()
