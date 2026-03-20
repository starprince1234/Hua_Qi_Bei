from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.constants import SUPPORTED_INDUSTRIES, REPORT_STYLES


class PredictRequest(BaseModel):
    file_id: str = Field(..., description="File ID returned by the upload endpoint")
    horizon: Literal[1, 3, 7, 14, 30] = Field(7, description="Prediction horizon in days")
    include_explainability: bool = Field(True, description="Include SHAP factor contributions")
    include_knowledge_graph: bool = Field(False, description="Include knowledge graph transmission paths")
    report_style: Literal["banking", "general"] = Field("general", description="Report style")
    industries: list[str] = Field(
        default_factory=lambda: list(SUPPORTED_INDUSTRIES),
        description="Industries to analyse for impact",
    )
