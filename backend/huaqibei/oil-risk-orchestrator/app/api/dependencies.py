from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.settings import Settings, get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(
    api_key: str | None = Security(_api_key_header),
    settings: Settings = Depends(get_settings),
) -> None:
    """Validate the X-API-Key header when API_KEY is configured."""
    if settings.API_KEY is None:
        return  # auth disabled
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def generate_request_id() -> str:
    """Generate a unique request ID for tracing."""
    return str(uuid.uuid4())
