"""
As-of 时间对齐器

职责：
    - 将宏观因子数据按"截至某日可观测"的逻辑与油价数据对齐
    - 防止未来数据泄露到训练/推理特征中
    - 输出按油价日期索引、已对齐的宏观因子矩阵

禁止：
    - 在此文件中做 lag 特征构造
    - 在此文件中调用模型
"""

from app.core.logger import get_logger

logger = get_logger(__name__)


class AsofAligner:
    """
    As-of 对齐器。

    策略：
        对于每个油价日期 t，提取宏观因子中 <= t 的最新可用观测值。
        这遵循"点时间"原则，确保推理阶段不引入未来信息。
    """

    def align(
        self,
        oil_dates: list[str],
        macro_records: list[dict],
    ) -> dict[str, dict]:
        """
        执行 as-of 对齐。

        Args:
            oil_dates: 油价日期列表（YYYY-MM-DD，升序）。
            macro_records: 宏观因子记录列表，每条需含 date 字段。

        Returns:
            {oil_date: macro_factor_dict} 映射字典。
            若某油价日期无可用宏观数据，则返回空字典 {}。
        """
        if not macro_records:
            logger.warning("宏观因子为空，返回全空对齐结果")
            return {d: {} for d in oil_dates}

        # 按日期排序宏观数据
        sorted_macro = sorted(macro_records, key=lambda r: r["date"])

        result: dict[str, dict] = {}

        macro_index = 0
        latest_macro: dict = {}

        for oil_date in oil_dates:
            # 推进宏观指针到 <= oil_date 的最大位置
            while (
                macro_index < len(sorted_macro)
                and sorted_macro[macro_index]["date"] <= oil_date
            ):
                latest_macro = {
                    k: v
                    for k, v in sorted_macro[macro_index].items()
                    if k != "date"
                }
                macro_index += 1

            result[oil_date] = dict(latest_macro)

        aligned_count = sum(1 for v in result.values() if v)
        logger.info(
            f"As-of 对齐完成 total={len(oil_dates)} "
            f"aligned={aligned_count} "
            f"empty={len(oil_dates) - aligned_count}"
        )

        return result
