from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx

from app.core.settings import get_settings


@asynccontextmanager
async def get_async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Yield a configured async httpx client with timeout and retry transport."""
    settings = get_settings()
    transport = httpx.AsyncHTTPTransport(retries=settings.MODEL_SERVICE_RETRIES)
    timeout = httpx.Timeout(settings.MODEL_SERVICE_TIMEOUT)
    async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
        yield client
