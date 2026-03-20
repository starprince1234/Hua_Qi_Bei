"""
应用配置（从环境变量读取）
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """所有可通过环境变量覆盖的配置项。"""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── 应用基础 ────────────────────────────────────────────────
    APP_NAME: str = "Oil Risk Intelligence Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── 模型 API ────────────────────────────────────────────────
    MODEL_API_URL: str = "http://localhost:8001"
    MODEL_API_KEY: str = ""
    MODEL_API_TIMEOUT: int = 30
    MODEL_API_MAX_RETRIES: int = 3
    MODEL_API_MODEL_ID: str = "oil-risk-v1"

    # ── LLM 配置 ────────────────────────────────────────────────
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_TIMEOUT: int = 60
    LLM_TOP_P: float = 0.9
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_MAX_TOKENS: int = 1500

    LLM_MODEL_RISK_LEVEL: str = "gpt-4o-mini"
    LLM_MODEL_INDUSTRY_IMPACT: str = "gpt-4o-mini"
    LLM_MODEL_KNOWLEDGE_GRAPH: str = "gpt-4o-mini"

    LLM_SYSTEM_PROMPT_RISK_DETAIL: str = (
        "你是一个专业的原油风险分析师，请根据以下预测数据给出简洁的风险评级与详情说明。"
    )
    LLM_SYSTEM_PROMPT_INDUSTRY_DETAIL: str = (
        "你是一个产业链分析师，请根据油价预测收益率分析各行业所受冲击，说明百分比来源与计算逻辑。"
    )
    LLM_SYSTEM_PROMPT_KG_DETAIL: str = (
        "你是一个知识图谱与产业传导专家，请根据传导路径分析各节点的影响等级与传导机制。"
    )

    # ── 上传 ────────────────────────────────────────────────────
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_FILE_SIZE_MB: int = 10

    # ── CORS ────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()
