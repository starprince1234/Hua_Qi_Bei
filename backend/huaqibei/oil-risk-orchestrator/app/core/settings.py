from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    # Application
    APP_NAME: str = "Oil Risk Intelligence Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Model service
    MODEL_SERVICE_URL: str = "http://localhost:8001"
    MODEL_SERVICE_TIMEOUT: int = 60  # seconds
    MODEL_SERVICE_RETRIES: int = 3

    # Security
    API_KEY: str | None = None

    # Logging
    LOG_LEVEL: str = "INFO"

    # Upload
    UPLOAD_DIR: str = "/tmp/oil_risk_uploads"
    MAX_UPLOAD_MB: int = 50

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]

    # LLM insight (optional)
    LLM_API_KEY: str | None = None
    LLM_API_URL: str = "https://api.openai.com/v1/chat/completions"
    LLM_MODEL: str = "gpt-4o-mini"

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
