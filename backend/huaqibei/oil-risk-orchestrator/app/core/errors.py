from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class OrchestratorError(Exception):
    """Base exception for all orchestrator errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict | None = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


class ValidationError(OrchestratorError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class ModelServiceError(OrchestratorError):
    status_code = 502
    error_code = "MODEL_SERVICE_ERROR"


class UploadError(OrchestratorError):
    status_code = 400
    error_code = "UPLOAD_ERROR"


class NotFoundError(OrchestratorError):
    status_code = 404
    error_code = "NOT_FOUND"


# ---------------------------------------------------------------------------
# FastAPI error handlers
# ---------------------------------------------------------------------------

async def orchestrator_error_handler(request: Request, exc: OrchestratorError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": str(exc),
        },
    )


def register_error_handlers(app) -> None:  # type: ignore[type-arg]
    """Register all custom error handlers on the FastAPI app."""
    app.add_exception_handler(OrchestratorError, orchestrator_error_handler)
    app.add_exception_handler(Exception, generic_error_handler)
