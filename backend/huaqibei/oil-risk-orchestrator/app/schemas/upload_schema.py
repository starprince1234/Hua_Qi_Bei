from __future__ import annotations

from pydantic import BaseModel, Field


class UploadData(BaseModel):
    file_id: str
    filename: str
    size: int = Field(..., description="File size in bytes")
    preview: list[dict] = Field(default_factory=list, description="First few rows of the uploaded data")


class UploadResponse(BaseModel):
    success: bool
    data: UploadData
