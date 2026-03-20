"""Model service API placeholder routes that mirror model-service-openapi.yaml."""

from fastapi import APIRouter, Header, Response, status
from fastapi.responses import JSONResponse

from app.core.settings import settings
from app.schemas.model_service_schema import (
    HealthResponse,
    MetadataResponse,
    ModelErrorResponse,
    ModelPredictRequest,
    ModelPredictResponse,
    ReturnQuantilePoint,
    SchemaResponse,
)

router = APIRouter(prefix="/model/v1", tags=["ModelServicePlaceholder"])


def _error(code: int, message: str, request_id: str | None = None) -> JSONResponse:
    payload = ModelErrorResponse(
        success=False,
        code=code,
        message=message,
        details={"placeholder": True},
        request_id=request_id,
    )
    return JSONResponse(status_code=code, content=payload.model_dump())


@router.get(
    "/health",
    summary="Health check",
    response_model=HealthResponse,
    responses={
        200: {"model": HealthResponse},
    },
)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", version=settings.APP_VERSION, uptime_sec=0)


@router.get(
    "/metadata",
    summary="Get model metadata",
    response_model=MetadataResponse,
)
async def metadata() -> MetadataResponse:
    return MetadataResponse(
        model_version="placeholder-model-v1",
        feature_config_version="placeholder-feature-config-v1",
        scaler_version="placeholder-scaler-v1",
        feature_names=["feature_1", "feature_2"],
    )


@router.get(
    "/schema",
    summary="Get request/response schema objects",
    response_model=SchemaResponse,
)
async def schema() -> SchemaResponse:
    return SchemaResponse(
        request_schema=ModelPredictRequest.model_json_schema(),
        response_schema=ModelPredictResponse.model_json_schema(),
    )


@router.post(
    "/predict/returns",
    summary="Predict future return quantiles",
    response_model=ModelPredictResponse,
    responses={
        400: {"model": ModelErrorResponse},
        422: {"model": ModelErrorResponse},
        429: {"model": ModelErrorResponse},
        503: {"model": ModelErrorResponse},
        500: {"model": ModelErrorResponse},
    },
)
async def predict_returns(
    request: ModelPredictRequest,
    response: Response,
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_signature_timestamp: str | None = Header(default=None, alias="X-Signature-Timestamp"),
) -> ModelPredictResponse | JSONResponse:
    del x_signature
    del x_signature_timestamp

    if request.target != "log_return":
        return _error(422, "FEATURE_CONFIG_MISMATCH", request.request_id)

    quantile_rows: list[ReturnQuantilePoint] = []
    for t in range(1, request.horizon + 1):
        quantile_rows.append(ReturnQuantilePoint(t=t, q05=-0.02, q50=0.001, q95=0.02))

    response.status_code = status.HTTP_200_OK
    return ModelPredictResponse(
        request_id=x_request_id or request.request_id,
        model_version=request.model_version,
        horizon=request.horizon,
        return_quantiles=quantile_rows,
        confidence_score=0.8,
        risk_level="MEDIUM",
        shap=None,
        warnings=[],
        latency_ms=1,
    )
