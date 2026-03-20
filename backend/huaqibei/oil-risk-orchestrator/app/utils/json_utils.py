"""
JSON 工具函数
"""

import json
from typing import Any


def safe_json_dumps(obj: Any, **kwargs) -> str:
    """
    安全序列化为 JSON 字符串，遇到不可序列化对象转为字符串。

    Args:
        obj: 任意 Python 对象。

    Returns:
        JSON 字符串。
    """

    def _default(o: Any) -> Any:
        if hasattr(o, "model_dump"):
            return o.model_dump()
        if hasattr(o, "__dict__"):
            return o.__dict__
        return str(o)

    return json.dumps(obj, ensure_ascii=False, default=_default, **kwargs)


def safe_json_loads(text: str) -> Any:
    """
    安全解析 JSON，失败时返回空字典。

    Args:
        text: JSON 字符串。

    Returns:
        解析后的 Python 对象，失败时返回 {}。
    """
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        # 尝试提取花括号内容
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except (json.JSONDecodeError, TypeError):
                pass
        return {}
