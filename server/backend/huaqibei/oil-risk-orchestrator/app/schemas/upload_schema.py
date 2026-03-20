"""上传相关 Schema。"""

from pydantic import BaseModel, Field
from typing import Any, Optional


class RepairLogItem(BaseModel):
    field: str
    strategy: str
    count: int
    severity: str = "warning"
    before_after_sample: Optional[dict[str, Any]] = None


class ValidationResult(BaseModel):
    passed: bool
    row_count: int
    date_range: Optional[list[str]] = None
    frequency_detected: Optional[str] = None
    required_columns_missing: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SchemaHint(BaseModel):
    required_columns: list[str] = Field(default_factory=list)
    optional_columns: list[str] = Field(default_factory=list)


class UploadResult(BaseModel):
    file_id: str
    detected_format: str
    validation: ValidationResult
    repair_log: list[RepairLogItem] = Field(default_factory=list)
    preview: list[dict[str, Any]] = Field(default_factory=list)
    schema_hint: SchemaHint
