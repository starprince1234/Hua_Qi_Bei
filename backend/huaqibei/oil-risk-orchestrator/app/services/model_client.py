"""
模型推理客户端（HTTP 封装）
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

MODEL_SERVICE_BASE_URL: str = os.getenv("MODEL_SERVICE_BASE_URL", "http://127.0.0.1:9000/model/v1")
MODEL_SERVICE_TIMEOUT: float = float(os.getenv("MODEL_SERVICE_TIMEOUT", "30"))
MODEL_SERVICE_API_KEY: str = os.getenv("MODEL_SERVICE_API_KEY", "")


def _headers() -> Dict[str, str]:
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    if MODEL_SERVICE_API_KEY:
        headers["Authorization"] = f"Bearer {MODEL_SERVICE_API_KEY}"
    return headers


def predict(
    features: Dict[str, float],
    horizon: str,
    include_shap: bool = False,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    调用远端模型服务的 /predict/returns 接口。

    Parameters
    ----------
    features:
        特征名称到数值的映射。
    horizon:
        预测时间窗口标识，如 ``"1D"``、``"7D"``。
    include_shap:
        是否在响应中包含 SHAP 归因值。
    request_id:
        可选请求追踪 ID，透传给下游服务。

    Returns
    -------
    Dict[str, Any]
        模型服务返回的原始 JSON 响应体。
    """
    payload: Dict[str, Any] = {
        "features": features,
        "horizon": horizon,
        "include_shap": include_shap,
    }
    if request_id:
        payload["request_id"] = request_id

    with httpx.Client(timeout=MODEL_SERVICE_TIMEOUT) as client:
        response = client.post(
            f"{MODEL_SERVICE_BASE_URL}/predict/returns",
            json=payload,
            headers=_headers(),
        )
        response.raise_for_status()
        return response.json()


def health_check() -> Dict[str, Any]:
    """检查模型服务健康状态。"""
    with httpx.Client(timeout=10.0) as client:
        response = client.get(f"{MODEL_SERVICE_BASE_URL}/health", headers=_headers())
        response.raise_for_status()
        return response.json()
