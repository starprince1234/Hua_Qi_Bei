from __future__ import annotations

import pandas as pd

from app.core.settings import get_settings
from app.core.errors import ModelServiceError
from app.core.logger import get_logger
from app.schemas.model_service_schema import ModelPredictRequest
from app.schemas.model_response_schema import ModelPredictResponse, RiskMetrics
from app.utils.http_client import get_async_client
from app.utils.json_utils import nan_safe_list

logger = get_logger(__name__)


async def call_model(df: pd.DataFrame, horizon: int, include_shap: bool = True) -> ModelPredictResponse:
    """Send feature matrix to the remote model service and return the parsed response."""
    settings = get_settings()
    feature_names = df.columns.tolist()
    features = nan_safe_list(df.values.tolist())

    payload = ModelPredictRequest(
        features=features,
        feature_names=feature_names,
        horizon=horizon,
        include_shap=include_shap,
        include_quantiles=True,
    )

    url = f"{settings.MODEL_SERVICE_URL}/predict"
    try:
        async with get_async_client() as client:
            resp = await client.post(url, json=payload.model_dump())
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        logger.warning("Model service unavailable, using mock", extra={"error": str(exc)})
        return _mock_response(len(df), horizon, feature_names, include_shap)

    return ModelPredictResponse(**data)


def _mock_response(
    n_samples: int,
    horizon: int,
    feature_names: list[str],
    include_shap: bool,
) -> ModelPredictResponse:
    """Generate a deterministic mock response for offline testing."""
    import math

    base_price = 85.0
    predictions = [base_price + math.sin(i * 0.3) * 2 for i in range(horizon)]
    quantile_keys = ["0.05", "0.10", "0.25", "0.50", "0.75", "0.90", "0.95"]
    offsets = [-8, -5, -2.5, 0, 2.5, 5, 8]
    quantiles = {k: [base_price + o + math.sin(i * 0.3) for i in range(horizon)] for k, o in zip(quantile_keys, offsets)}

    shap_values = None
    if include_shap and feature_names:
        import random
        rng = random.Random(42)
        shap_values = [[rng.uniform(-0.5, 0.5) for _ in feature_names] for _ in range(min(n_samples, 10))]

    return ModelPredictResponse(
        predictions=predictions,
        quantiles=quantiles,
        shap_values=shap_values,
        feature_names=feature_names,
        risk_metrics=RiskMetrics(var_95=-4.5, cvar_95=-6.2, volatility=0.18),
        model_version="mock-1.0.0",
    )
