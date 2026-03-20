"""
滞后特征构造器

职责：
    - 为时间序列特征构造滞后项（lag features）
    - 构造滚动统计特征（rolling mean / rolling std）
    - 输出标准化特征矩阵

禁止：
    - 在此文件中做 as-of 对齐
    - 在此文件中调用模型
"""

from app.core.settings import settings
from app.core.constants import FEATURE_NA_FILL_VALUE
from app.core.logger import get_logger
from app.utils.math_utils import compute_log_return

logger = get_logger(__name__)


class LagBuilder:
    """
    滞后特征构造器。

    构造内容：
        1. 目标变量（油价对数收益率）的滞后项 lag_1 … lag_N
        2. close 价格的滚动均值和滚动标准差
        3. 对齐后宏观因子的滞后项
    """

    def __init__(
        self,
        lag_periods: list[int] | None = None,
        rolling_windows: list[int] | None = None,
    ) -> None:
        """
        初始化构造器。

        Args:
            lag_periods: 滞后期列表，默认使用 settings.DEFAULT_LAG_PERIODS。
            rolling_windows: 滚动窗口列表，默认使用 settings.DEFAULT_ROLLING_WINDOWS。
        """
        self._lag_periods = lag_periods or settings.DEFAULT_LAG_PERIODS
        self._rolling_windows = rolling_windows or settings.DEFAULT_ROLLING_WINDOWS

    def build_features(
        self,
        oil_records: list[dict],
        aligned_macro: dict[str, dict] | None = None,
    ) -> list[dict]:
        """
        构造完整特征矩阵。

        Args:
            oil_records: 已填充缺失值的油价记录（含 date/close 等字段）。
            aligned_macro: as-of 对齐后的宏观因子映射（可选）。

        Returns:
            特征矩阵，每行为一个时间点的特征字典。
            最前面的行因滞后期不足会被过滤掉。
        """
        n = len(oil_records)
        closes = [r["close"] for r in oil_records]
        dates = [r["date"] for r in oil_records]

        # 计算对数收益率序列（长度 = n-1）
        log_returns = compute_log_return(closes)
        # 补齐第一个位置为 0
        log_returns = [FEATURE_NA_FILL_VALUE] + log_returns

        feature_rows: list[dict] = []

        for i, record in enumerate(oil_records):
            row: dict = {"date": record["date"], "close": record["close"]}

            # ─── 收益率滞后特征 ──────────────────────────────
            for lag in self._lag_periods:
                idx = i - lag
                key = f"return_lag_{lag}"
                row[key] = log_returns[idx] if idx >= 0 else FEATURE_NA_FILL_VALUE

            # ─── 滚动统计特征 ────────────────────────────────
            for window in self._rolling_windows:
                start = max(0, i - window + 1)
                window_closes = closes[start : i + 1]

                mean_key = f"rolling_mean_{window}"
                std_key = f"rolling_std_{window}"

                row[mean_key] = sum(window_closes) / len(window_closes)

                if len(window_closes) > 1:
                    mean_val = row[mean_key]
                    variance = sum(
                        (x - mean_val) ** 2 for x in window_closes
                    ) / (len(window_closes) - 1)
                    row[std_key] = variance ** 0.5
                else:
                    row[std_key] = FEATURE_NA_FILL_VALUE

            # ─── 宏观因子（若有）────────────────────────────
            if aligned_macro:
                macro = aligned_macro.get(record["date"], {})
                for macro_key, macro_val in macro.items():
                    row[f"macro_{macro_key}"] = (
                        macro_val if macro_val is not None else FEATURE_NA_FILL_VALUE
                    )

            # 目标变量（当前收益率，供参考，不作为输入特征）
            row["current_return"] = log_returns[i]

            feature_rows.append(row)

        # 过滤掉前 max_lag 行（特征不完整）
        max_lag = max(self._lag_periods) if self._lag_periods else 0
        valid_rows = feature_rows[max_lag:]

        logger.info(
            f"滞后特征构造完成 total={n} "
            f"valid={len(valid_rows)} "
            f"filtered={max_lag} rows"
        )

        return valid_rows
