"""
模型服务占位 Schema（供模型服务路由使用）
"""

from pydantic import BaseModel, Field
from typing import Optional


class ModelServiceHealthResponse(BaseModel):
    """模型服务健康检查响应。"""

    reachable: bool = Field(..., description="服务是否可达")
    model_id: str = Field(..., description="模型 ID")
    latency_ms: Optional[float] = Field(None, description="延迟（毫秒）")


class ModelServiceInfoResponse(BaseModel):
    """模型服务信息响应。"""

    model_id: str
    api_url: str
    mode: str = Field(..., description="调用模式：openai / legacy")
    supported_horizons: list[int] = Field(default_factory=list)
