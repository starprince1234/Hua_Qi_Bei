"""
时间对齐工具（as-of join / merge_asof）

职责：
    - 将不同频率的宏观因子与油价数据按日期对齐
    - 保证特征数组与目标数组在时间轴上严格对应
"""

from datetime import date, datetime
from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)


def parse_date(date_str: str) -> date:
    """解析日期字符串为 date 对象，支持多种格式。"""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"无法解析日期: {date_str}")


class AsofAligner:
    """
    As-of 时间对齐器。

    将稀疏宏观因子序列（如月度/周度）按最近前向填充方式对齐到日度序列。
    """

    def align(
        self,
        primary: list[dict[str, Any]],
        secondary: list[dict[str, Any]],
        primary_date_key: str = "date",
        secondary_date_key: str = "date",
        value_keys: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        对齐两个时序数据集。

        Args:
            primary: 主序列（日度），目标对齐基准。
            secondary: 次序列（稀疏），被对齐序列。
            primary_date_key: 主序列日期键名。
            secondary_date_key: 次序列日期键名。
            value_keys: 要从次序列提取的字段列表，None 则提取全部非日期字段。

        Returns:
            与 primary 等长的合并后记录列表。
        """
        if not secondary:
            return [dict(r) for r in primary]

        # 排序次序列
        sorted_secondary = sorted(
            secondary,
            key=lambda r: parse_date(str(r[secondary_date_key])),
        )

        all_value_keys = value_keys or [
            k for k in sorted_secondary[0].keys() if k != secondary_date_key
        ]

        # 构建 (date, values) 查找结构
        secondary_dated: list[tuple[date, dict[str, Any]]] = []
        for rec in sorted_secondary:
            try:
                d = parse_date(str(rec[secondary_date_key]))
                secondary_dated.append((d, {k: rec.get(k) for k in all_value_keys}))
            except ValueError:
                continue

        result: list[dict[str, Any]] = []
        ptr = 0
        last_values: dict[str, Any] = {}

        for rec in primary:
            try:
                pdate = parse_date(str(rec[primary_date_key]))
            except ValueError:
                result.append(dict(rec))
                continue

            while ptr < len(secondary_dated) and secondary_dated[ptr][0] <= pdate:
                last_values = secondary_dated[ptr][1]
                ptr += 1

            merged = dict(rec)
            merged.update(last_values)
            result.append(merged)

        logger.debug(f"AsofAligner: 对齐 {len(primary)} 条主序列记录")
        return result
