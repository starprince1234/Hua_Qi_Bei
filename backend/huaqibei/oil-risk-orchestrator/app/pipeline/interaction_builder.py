"""
特征交叉项构建器

职责：
    - 构造关键因子间的乘积交互特征
    - 增强模型对非线性关系的捕获能力
"""

from typing import Any

from app.core.logger import get_logger

logger = get_logger(__name__)

# 预定义交叉特征对：(特征A, 特征B, 输出名)
INTERACTION_PAIRS: list[tuple[str, str, str]] = [
    ("OVX", "DXY", "OVX_x_DXY"),
    ("OVX_日涨跌幅 (%)", "Brent_当日波动幅度(%)", "OVX_pct_x_Brent_vol"),
    ("T5YIE_30日差分", "DXY_7日滚动均值", "T5YIE_diff_x_DXY_ma7"),
    ("Gasoline_7日涨跌幅(%)", "Crack_Spread_3日差分", "Gasoline_pct_x_CrackSpread"),
]


class InteractionBuilder:
    """
    特征交叉项构建器。

    对数据集中的关键特征对构建乘积交叉项，丰富非线性表示。
    """

    def __init__(self, pairs: list[tuple[str, str, str]] | None = None) -> None:
        """
        初始化。

        Args:
            pairs: 自定义交叉对列表，None 时使用默认 INTERACTION_PAIRS。
        """
        self._pairs = pairs if pairs is not None else INTERACTION_PAIRS

    def build(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        对记录列表添加交叉特征。

        Args:
            records: 特征记录列表（每条为字典）。

        Returns:
            添加了交叉项后的新记录列表。
        """
        result: list[dict[str, Any]] = []
        added_count = 0

        for rec in records:
            new_rec = dict(rec)
            for feat_a, feat_b, out_name in self._pairs:
                val_a = rec.get(feat_a)
                val_b = rec.get(feat_b)
                if val_a is not None and val_b is not None:
                    try:
                        new_rec[out_name] = float(val_a) * float(val_b)
                        added_count += 1
                    except (TypeError, ValueError):
                        new_rec[out_name] = 0.0
                else:
                    new_rec[out_name] = 0.0
            result.append(new_rec)

        logger.debug(f"InteractionBuilder: 添加了 {len(self._pairs)} 个交叉特征，共 {added_count} 个非零值")
        return result
