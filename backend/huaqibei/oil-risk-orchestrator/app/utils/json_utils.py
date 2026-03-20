from __future__ import annotations

import json
import math
from typing import Any


class _NanSafeEncoder(json.JSONEncoder):
    """JSON encoder that converts NaN/Inf to None and numpy scalars to Python natives."""

    def default(self, obj: Any) -> Any:
        try:
            import numpy as np
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, np.floating):
                return None if math.isnan(float(obj)) else float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)

    def encode(self, obj: Any) -> str:
        return super().encode(_sanitize(obj))


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def safe_parse(text: str) -> Any:
    """Parse JSON string, returning None on failure."""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None


def pretty_format(obj: Any, indent: int = 2) -> str:
    """Serialise *obj* to a pretty-printed JSON string, NaN-safe."""
    return json.dumps(_sanitize(obj), ensure_ascii=False, indent=indent, cls=_NanSafeEncoder)


def nan_safe_list(data: list) -> list:
    """Recursively replace NaN/Inf floats with None in a nested list."""
    return _sanitize(data)  # type: ignore[return-value]
