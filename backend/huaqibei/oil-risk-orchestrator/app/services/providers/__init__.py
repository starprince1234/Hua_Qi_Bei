"""External intelligence provider seams for future live integrations.

The classes exported here are intentionally safe to import in M1 demo mode:
they do not read credentials, create network clients, or call third-party APIs.
"""

from .gdelt_provider import GDELTProvider
from .llm_analysis_provider import LLMAnalysisProvider
from .newsapi_fallback_provider import NewsAPIFallbackProvider

__all__ = [
    "GDELTProvider",
    "LLMAnalysisProvider",
    "NewsAPIFallbackProvider",
]
