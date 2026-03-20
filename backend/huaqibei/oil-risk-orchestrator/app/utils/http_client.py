"""
HTTP 客户端工具（封装 httpx 异步请求）
"""

from typing import Any, Optional
import httpx

from app.core.logger import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 30


async def post_json(
    url: str,
    payload: dict[str, Any],
    headers: Optional[dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    发送 POST JSON 请求并返回解析后的响应字典。

    Args:
        url: 目标 URL。
        payload: 请求体字典。
        headers: 自定义请求头。
        timeout: 超时秒数。

    Returns:
        响应 JSON 字典。

    Raises:
        httpx.HTTPStatusError: HTTP 4xx/5xx 状态码。
        httpx.RequestError: 网络错误。
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers or {})
        response.raise_for_status()
        return response.json()


async def get_json(
    url: str,
    headers: Optional[dict[str, str]] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """
    发送 GET 请求并返回解析后的响应字典。

    Args:
        url: 目标 URL。
        headers: 自定义请求头。
        timeout: 超时秒数。

    Returns:
        响应 JSON 字典。
    """
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(url, headers=headers or {})
        response.raise_for_status()
        return response.json()
