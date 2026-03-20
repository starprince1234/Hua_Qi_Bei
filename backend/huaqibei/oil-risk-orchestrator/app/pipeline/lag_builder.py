"""
滞后特征构建器

职责：
    - 为指定特征添加 N 日滞后值
    - 添加滚动均值、滚动标准差等时间窗口统计特征
"""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# 默认滞后配置：{特征名: [滞后天数列表]}
DEFAULT_LAG_CONFIG: dict[str, list[int]] = {
    "OVX": [1, 3, 7],
    "DXY": [1, 7],
    "T5YIE": [1, 7, 30],
    "Brent_Crude(BZ=F)_Close": [1, 3],
}

# 默认滚动统计配置：{特征名: [窗口列表]}
DEFAULT_ROLLING_CONFIG: dict[str, list[int]] = {
    "OVX": [3, 7],
    "Brent_Crude(BZ=F)_Close": [7, 14],
    "DXY": [7],
}


class LagBuilder:
    """
    滞后特征与滚动统计构建器。
    """

    def __init__(
        self,
        lag_config: dict[str, list[int]] | None = None,
        rolling_config: dict[str, list[int]] | None = None,
    ) -> None:
        self._lag_config = lag_config if lag_config is not None else DEFAULT_LAG_CONFIG
        self._rolling_config = rolling_config if rolling_config is not None else DEFAULT_ROLLING_CONFIG

    def build(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        为记录列表添加滞后特征与滚动统计特征。

        Args:
            records: 按时间升序排列的特征记录列表。

        Returns:
            添加了滞后/滚动特征后的新记录列表。
        """
        if not records:
            return []

        result = [dict(r) for r in records]
        n = len(result)

        # 添加滞后特征
        for feat, lags in self._lag_config.items():
            values = [r.get(feat) for r in records]
            for lag in lags:
                lag_key = f"{feat}_滞后{lag}日"
                for i in range(n):
                    if i >= lag and values[i - lag] is not None:
                        result[i][lag_key] = float(values[i - lag])
                    else:
                        result[i][lag_key] = 0.0

        # 添加滚动均值和标准差
        import math

        for feat, windows in self._rolling_config.items():
            values = [float(r.get(feat, 0.0) or 0.0) for r in records]
            for window in windows:
                ma_key = f"{feat}_{window}日滚动均值"
                std_key = f"{feat}_{window}日滚动标准差"
                for i in range(n):
                    if i < window - 1:
                        result[i][ma_key] = 0.0
                        result[i][std_key] = 0.0
                    else:
                        window_vals = values[i - window + 1 : i + 1]
                        mean = sum(window_vals) / window
                        variance = sum((v - mean) ** 2 for v in window_vals) / window
                        result[i][ma_key] = round(mean, 6)
                        result[i][std_key] = round(math.sqrt(variance), 6)

        logger.debug(f"LagBuilder: 处理 {n} 条记录，添加滞后和滚动特征")
        return result
