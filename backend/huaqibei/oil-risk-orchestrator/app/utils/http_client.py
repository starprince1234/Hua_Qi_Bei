"""
HTTP 客户端工具

职责：
    - 提供可复用的 async HTTPX 会话
    - 统一超时与重试配置
    - 所有模块通过此工具发起外部 HTTP 请求

禁止：
    - 直接在路由或 Service 层实例化 httpx.AsyncClient
"""

import httpx
from typing import Optional, Any
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


async def post_json(
    url: str,
    payload: dict[str, Any],
    headers: Optional[dict[str, str]] = None,
    timeout: int = 30,
) -> dict[str, Any]:
    """
    发起异步 POST JSON 请求。

    Args:
        url: 目标 URL。
        payload: 请求体字典。
        headers: 额外请求头（可选）。
        timeout: 超时秒数。

    Returns:
        响应 JSON 字典。

    Raises:
        httpx.HTTPStatusError: HTTP 4xx/5xx 错误。
        httpx.TimeoutException: 请求超时。
        httpx.RequestError: 网络层错误。
    """
    default_headers = {"Content-Type": "application/json"}
    if headers:
        default_headers.update(headers)

    logger.debug(f"POST {url} payload_keys={list(payload.keys())}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=default_headers)
        response.raise_for_status()
        return response.json()


async def get_json(
    url: str,
    params: Optional[dict[str, Any]] = None,
    headers: Optional[dict[str, str]] = None,
    timeout: int = 15,
) -> dict[str, Any]:
    """
    发起异步 GET JSON 请求。

    Args:
        url: 目标 URL。
        params: 查询参数（可选）。
        headers: 额外请求头（可选）。
        timeout: 超时秒数。

    Returns:
        响应 JSON 字典。
    """
    logger.debug(f"GET {url} params={params}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
