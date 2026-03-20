"""Model service OpenAPI contract placeholder schemas."""

from pydantic import BaseModel, Field
from typing import Any


class ModelErrorResponse(BaseModel):
    success: bool = Field(default=False)
    code: int
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str | None = None


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    version: str
    uptime_sec: int = Field(default=0, ge=0)


class MetadataCapabilities(BaseModel):
    return_shap: bool = True
    multi_quantile: bool = True
    batch_inference: bool = True


class MetadataResponse(BaseModel):
    model_version: str
    feature_config_version: str
    scaler_version: str
    feature_names: list[str]
    target: str = "log_return"
    supported_quantiles: list[float] = Field(default_factory=lambda: [0.05, 0.5, 0.95])
    max_horizon: int = 60
    capabilities: MetadataCapabilities = Field(default_factory=MetadataCapabilities)


class SchemaResponse(BaseModel):
    request_schema: dict[str, Any]
    response_schema: dict[str, Any]


class PredictOptions(BaseModel):
    return_shap: bool = False
    shap_topk: int = Field(default=15, ge=1, le=200)


class ModelPredictRequest(BaseModel):
    request_id: str
    as_of: str
    horizon: int = Field(ge=1, le=60)
    quantiles: list[float] = Field(min_length=2)
    target: str = "log_return"
    feature_names: list[str] = Field(min_length=1)
    timestamps: list[str] = Field(min_length=1)
    X: list[list[float]]
    model_version: str
    feature_config_version: str
    scaler_version: str
    options: PredictOptions | None = None


class ReturnQuantilePoint(BaseModel):
    t: int = Field(ge=1)
    q05: float
    q50: float
    q95: float


class SHAPItem(BaseModel):
    factor: str
    value: float
    shap: float


class SHAPPayload(BaseModel):
    top_factors: list[SHAPItem] = Field(default_factory=list)
    base_value: float = 0.0


class ModelWarning(BaseModel):
    type: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ModelPredictResponse(BaseModel):
    request_id: str
    model_version: str
    horizon: int
    return_quantiles: list[ReturnQuantilePoint]
    confidence_score: float = Field(ge=0, le=1)
    risk_level: str
    shap: SHAPPayload | None = None
    warnings: list[ModelWarning] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
