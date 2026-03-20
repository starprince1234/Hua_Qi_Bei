from __future__ import annotations

import logging
import sys
from typing import Any


class _JsonFormatter(logging.Formatter):
    """Minimal JSON-like structured formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        # Flatten any extra keys added via `extra=`
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord.__dict__ and key not in payload:
                payload[key] = value
        import json
        return json.dumps(payload, ensure_ascii=False, default=str)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Return a structured logger for *name*."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # already configured

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.propagate = False
    return logger
