"""统一业务异常与错误码。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class BusinessErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"
    FREQUENCY_MISMATCH = "FREQUENCY_MISMATCH"
    ASOF_LEAKAGE = "ASOF_LEAKAGE"
    MODEL_TIMEOUT = "MODEL_TIMEOUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    REPORT_SCHEMA_INVALID = "REPORT_SCHEMA_INVALID"
    UNSUPPORTED_FILE_TYPE = "UNSUPPORTED_FILE_TYPE"
    PARSING_ERROR = "PARSING_ERROR"


@dataclass
class BusinessError(Exception):
    code: BusinessErrorCode
    message: str
    status_code: int = 400
    details: Optional[Any] = None

    def __str__(self) -> str:
        return f"{self.code.value}: {self.message}"
