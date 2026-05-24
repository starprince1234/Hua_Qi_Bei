"""
系统核心配置模块

职责：
    - 集中管理所有可配置参数
    - 通过环境变量注入，支持 Docker 部署
    - 不允许在其他模块中硬编码配置值

禁止：
    - 在此文件中写业务逻辑
    - 在此文件中写数据处理
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """全局系统配置，所有配置项均可通过环境变量覆盖。"""

    # ─── 应用基础信息 ──────────────────────────────────────────────
    APP_NAME: str = "Oil Risk Intelligence Orchestrator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # ─── 服务器配置 ────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ─── 云端模型 API 配置 ──────────────────────────────────────────
    MODEL_API_URL: str = "http://localhost:9000/predict/returns"
    MODEL_API_TIMEOUT: int = 30          # 秒
    MODEL_API_MAX_RETRIES: int = 3
    MODEL_API_KEY: Optional[str] = None  # Bearer Token，可选
    MODEL_API_MODEL_ID: str = "oil_vol_model"

    # ─── LLM 报告生成配置（Provider 可切换） ────────────────────────
    LLM_PROVIDER: str = "siliconflow"  # openai | xf_maas | siliconflow
    LLM_BASE_URL: str = "https://api.siliconflow.cn/v1"
    LLM_API_KEY: str = ""
    LLM_MODEL_ID: str = "Pro/deepseek-ai/DeepSeek-V3.2"
    LLM_JSON_MODE: bool = True
    LLM_LORA_ID: Optional[str] = None
    LLM_SEARCH_DISABLE: bool = True
    LLM_MAX_TOKENS: int = 1500
    LLM_TEMPERATURE: float = 0.3
    LLM_TOP_P: float = 0.7
    LLM_TOP_K: int = 50
    LLM_FREQUENCY_PENALTY: float = 0.2
    LLM_ENABLE_THINKING: bool = False
    LLM_THINKING_BUDGET: int = 4096
    LLM_TIMEOUT: int = 60
    LLM_MAX_RETRIES: int = 1
    INDUSTRY_LLM_ENABLED: bool = False

    # ─── 分模块 LLM 配置（并发调用） ─────────────────────────────────
    LLM_MODEL_RISK_LEVEL: str = "Pro/deepseek-ai/DeepSeek-V3.2"
    LLM_MODEL_INDUSTRY_IMPACT: str = "deepseek-ai/DeepSeek-V3.2"
    LLM_MODEL_KNOWLEDGE_GRAPH: str = "deepseek-ai/DeepSeek-V3.1-Terminus"
    LLM_MODEL_REPORT_SUMMARY: str = "Pro/deepseek-ai/DeepSeek-V3.1-Terminus"
    LLM_MODEL_FINANCING_RECOMMENDATION: str = "Qwen/Qwen3.5-397B-A17B"

    LLM_SYSTEM_PROMPT_RISK_DETAIL: str = (
        "You are a banking risk interpretation assistant. Determine a risk level (LOW/MEDIUM/HIGH) "
        "from the provided quantitative forecast data, and provide a concise, auditable explanation "
        "that explicitly cites numeric evidence from the input. English only."
    )
    LLM_SYSTEM_PROMPT_INDUSTRY_DETAIL: str = (
        "You are an industry shock analysis assistant. Explain the basis of each industry shock percentage "
        "and the transmission logic. Use only the industry sensitivity, direction, and magnitude provided "
        "in the input. Do not invent new industries. English only."
    )
    LLM_SYSTEM_PROMPT_KG_DETAIL: str = (
        "You are a knowledge-graph transmission analysis assistant. Analyze by industry and by node: "
        "1) Create a dedicated subsection per industry with the full transmission path; "
        "2) For each node, explain impact direction, intensity, reason, and transmission to the next node; "
        "3) For each node, assign one impact level strictly from: CRITICAL/HIGH/MEDIUM/LOW/MINOR/NONE; "
        "4) End with cross-industry comparison and key vulnerable nodes; "
        "5) The detail section must be comprehensive, not brief. English only."
    )
    LLM_SYSTEM_PROMPT_REPORT_SUMMARY: str = (
        "You are a senior energy finance risk analyst for enterprise banking. "
        "Output a professional, actionable, and evidence-based report summary in English only, "
        "covering trend, key drivers, industry impact, and risk limits."
    )
    LLM_SYSTEM_PROMPT_FINANCING_RECOMMENDATION: str = (
        "You are a senior energy commodity finance strategist with 15+ years of experience at top-tier "
        "investment banks. You must generate an English-only financing recommendation report based strictly "
        "on provided prediction facts and factor drivers. "
        "Your report must include: "
        "(1) Oil price trend and driver logic review, "
        "(2) Entity-specific decision conversion recommendations, "
        "(3) Implementation safeguards and differentiation advantages. "
        "For entity recommendations, cover all required modules for real-sector entities: financing advice, "
        "procurement rhythm, inventory management, and hedging arrangement. "
        "If information is missing, state explicit assumptions before recommendations. "
        "Comply with financial regulations and avoid speculative or unsupported claims."
    )

    # # 兼容旧字段（逐步废弃）
    # LLM_API_URL: str = "https://api.openai.com/v1/chat/completions"
    # LLM_MODEL: str = "gpt-4o-mini"
    # LLM_MAX_TOKENS: int = 1500
    # LLM_TEMPERATURE: float = 0.3
    # LLM_TIMEOUT: int = 60

    # ─── 风险分级阈值 ───────────────────────────────────────────────
    RISK_LOW_THRESHOLD: float = 0.03     # 收益率变化 < 3% → 低风险
    RISK_MEDIUM_THRESHOLD: float = 0.07  # 3% ≤ 变化 < 7% → 中风险
    # > 7% → 高风险

    # ─── 特征工程配置 ───────────────────────────────────────────────
    DEFAULT_LAG_PERIODS: list[int] = [1, 3, 5, 10, 20]
    DEFAULT_ROLLING_WINDOWS: list[int] = [5, 10, 20]
    MAX_FEATURE_MISSING_RATIO: float = 0.3  # 缺失率超过此阈值则拒绝

    # ─── 数据路径配置 ───────────────────────────────────────────────
    FACTOR_DICTIONARY_PATH: str = "data/factor_dictionary.json"
    KNOWLEDGE_GRAPH_PATH: str = "app/knowledge_graph/graph_data.json"
    UPLOAD_TEMPLATE_DIR: str = "data/templates"

    # ─── CORS 配置 ─────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = ["*"]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中未声明的字段（如 USE_MOCK_MODEL）


# 全局单例
settings = Settings()
