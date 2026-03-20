from __future__ import annotations

from pydantic import BaseModel, Field


class ReportSection(BaseModel):
    title: str
    content: str
    charts: list[dict] = Field(default_factory=list)


class ReportRequest(BaseModel):
    file_id: str
    style: str = "general"


class ReportResponse(BaseModel):
    file_id: str
    style: str
    title: str
    generated_at: str
    summary: ReportSection
    detail: ReportSection
    risk_section: ReportSection | None = None
    industry_section: ReportSection | None = None
    charts: list[dict] = Field(default_factory=list)
