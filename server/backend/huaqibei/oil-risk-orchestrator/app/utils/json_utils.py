"""
JSON 工具函数

职责：
    - 安全的 JSON 序列化/反序列化
    - 支持 datetime、float special values 处理
"""

import json
import uuid
from datetime import datetime
from typing import Any


class SafeJSONEncoder(json.JSONEncoder):
    """支持 datetime 和 float 特殊值的 JSON 编码器。"""

    def default(self, obj: Any) -> Any:
        """处理不可序列化对象。"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

    def encode(self, obj: Any) -> str:
        """覆写 encode 处理 NaN/Inf。"""
        # 将 Python float NaN/Inf 转为 null
        def _clean(o: Any) -> Any:
            if isinstance(o, float):
                import math
                if math.isnan(o) or math.isinf(o):
                    return None
            elif isinstance(o, dict):
                return {k: _clean(v) for k, v in o.items()}
            elif isinstance(o, list):
                return [_clean(i) for i in o]
            return o

        return super().encode(_clean(obj))


def safe_json_dumps(obj: Any, indent: int | None = None) -> str:
    """
    安全序列化为 JSON 字符串。

    Args:
        obj: 待序列化对象。
        indent: 缩进空格数（None 为紧凑格式）。

    Returns:
        JSON 字符串。
    """
    return json.dumps(obj, cls=SafeJSONEncoder, ensure_ascii=False, indent=indent)


def safe_json_loads(text: str) -> Any:
    """
    安全反序列化 JSON 字符串。

    Args:
        text: JSON 字符串。

    Returns:
        Python 对象。

    Raises:
        json.JSONDecodeError: 格式非法时抛出。
    """
    return json.loads(text)


def generate_request_id() -> str:
    """
    生成唯一请求追踪 ID。

    Returns:
        UUID4 字符串。
    """
    return str(uuid.uuid4())
