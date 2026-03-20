from __future__ import annotations

from pydantic import BaseModel, Field


class IndustryImpact(BaseModel):
    industry: str = Field(..., description="Industry identifier: aviation | shipping | chemical")
    impact_score: float = Field(..., description="Normalised impact score [-1, 1]")
    direction: str = Field(..., description="'up' | 'down' | 'neutral'")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in the impact estimate")
    description: str = Field("", description="Plain-language Chinese description of the impact")
