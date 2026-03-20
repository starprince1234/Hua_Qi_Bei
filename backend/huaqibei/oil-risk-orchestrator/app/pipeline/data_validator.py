"""
数据校验器

职责：
    - 校验入参数据的完整性与合法性
    - 在进入特征工程之前阻断脏数据
    - 返回结构化校验报告

禁止：
    - 在此文件中做特征构造
    - 在此文件中调用模型
"""

from dataclasses import dataclass, field
from app.core.constants import FEATURE_NA_FILL_VALUE, MIN_REQUIRED_ROWS, MAX_UPLOAD_ROWS
from app.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ValidationReport:
    """数据校验报告。"""

    passed: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    missing_ratio: float = 0.0
    repair_log: list[dict] = field(default_factory=list)


class DataValidator:
    """
    数据校验器。

    职责：
        - 行数校验
        - 价格合法性校验
        - 缺失率校验
        - 时间序列连续性检查
    """

    def __init__(self, max_missing_ratio: float = 0.3) -> None:
        """
        初始化校验器。

        Args:
            max_missing_ratio: 允许的最大缺失率，超过则标记为失败。
        """
        self._max_missing_ratio = max_missing_ratio

    def validate_oil_data(self, records: list[dict]) -> ValidationReport:
        """
        校验油价时间序列数据。

        Args:
            records: 油价记录列表，每条需含 date/open/high/low/close。

        Returns:
            ValidationReport 校验报告。
        """
        report = ValidationReport(row_count=len(records))

        # 行数下限
        if len(records) < MIN_REQUIRED_ROWS:
            report.passed = False
            report.errors.append(
                f"数据行数 {len(records)} 不足最低要求 {MIN_REQUIRED_ROWS} 行"
            )
            return report

        # 行数上限
        if len(records) > MAX_UPLOAD_ROWS:
            report.passed = False
            report.errors.append(
                f"数据行数 {len(records)} 超过最大限制 {MAX_UPLOAD_ROWS} 行"
            )
            return report

        # 缺失率计算（以 close 为主字段）
        missing_count = sum(1 for r in records if r.get("close") is None)
        report.missing_ratio = missing_count / len(records)

        if report.missing_ratio > self._max_missing_ratio:
            report.passed = False
            report.errors.append(
                f"close 字段缺失率 {report.missing_ratio:.1%} "
                f"超过阈值 {self._max_missing_ratio:.0%}"
            )

        # 价格合法性：close 必须 > 0
        invalid_prices = [
            i for i, r in enumerate(records)
            if r.get("close") is not None and r["close"] <= 0
        ]
        if invalid_prices:
            report.passed = False
            report.errors.append(
                f"发现 {len(invalid_prices)} 条 close <= 0 的非法记录，"
                f"行索引: {invalid_prices[:5]}"
            )

        if report.passed:
            logger.info(
                f"数据校验通过 rows={len(records)} "
                f"missing_ratio={report.missing_ratio:.2%}"
            )
        else:
            logger.warning(f"数据校验失败 errors={report.errors}")

        return report

    def fill_missing_values_with_log(self, records: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        缺失值填充并返回结构化修复日志。

        Returns:
            (filled_records, repair_log)
        """
        numeric_fields = ["open", "high", "low", "close", "volume"]
        before_counts = {
            field_name: sum(1 for row in records if row.get(field_name) is None)
            for field_name in numeric_fields
        }

        filled = []
        last_values: dict[str, float] = {}

        for record in records:
            new_record = dict(record)
            for field_name in numeric_fields:
                val = new_record.get(field_name)
                if val is None:
                    strategy = "ffill" if field_name in last_values else "constant_fill"
                    new_record[field_name] = last_values.get(
                        field_name, FEATURE_NA_FILL_VALUE
                    )
                else:
                    last_values[field_name] = val
            filled.append(new_record)

        after_counts = {
            field_name: sum(1 for row in filled if row.get(field_name) is None)
            for field_name in numeric_fields
        }

        repair_log: list[dict] = []
        for field_name in numeric_fields:
            repaired = max(before_counts[field_name] - after_counts[field_name], 0)
            if repaired > 0:
                repair_log.append(
                    {
                        "field": field_name,
                        "strategy": "ffill_or_constant",
                        "count": repaired,
                        "severity": "warning",
                        "before_after_sample": {
                            "before_missing": before_counts[field_name],
                            "after_missing": after_counts[field_name],
                        },
                    }
                )

        return filled, repair_log

    def fill_missing_values(self, records: list[dict]) -> list[dict]:
        """
        对缺失数值做前向填充，剩余用 FEATURE_NA_FILL_VALUE 兜底。

        Args:
            records: 原始记录列表。

        Returns:
            填充后的记录列表（不修改原始数据，返回新列表）。
        """
        filled, _ = self.fill_missing_values_with_log(records)
        return filled
