"""
交互特征构造器

职责：
    - 构造因子之间的交互项（乘积特征、比值特征）
    - 提升模型对非线性关系的捕捉能力

禁止：
    - 在此文件中做 lag 计算
    - 在此文件中做模型调用
"""

from app.core.logger import get_logger
from app.utils.math_utils import safe_divide

logger = get_logger(__name__)


class InteractionBuilder:
    """
    交互特征构造器。

    规则：
        1. 油价收益率 × DXY（美元指数）→ 汇率-油价联动项
        2. 油价收益率 × VIX（恐慌指数）→ 波动率-油价联动项
        3. 滚动均值 / 滚动标准差 → Sharpe-like 波动调整因子
        4. EIA 库存变化 × 价格滞后项 → 供需动量
    """

    def build_interactions(self, feature_rows: list[dict]) -> list[dict]:
        """
        在已有特征矩阵基础上叠加交互项。

        Args:
            feature_rows: LagBuilder 输出的特征矩阵。

        Returns:
            叠加了交互特征的新特征矩阵（不修改原始数据）。
        """
        enriched: list[dict] = []

        for row in feature_rows:
            new_row = dict(row)

            return_lag_1 = row.get("return_lag_1", 0.0) or 0.0
            rolling_mean_5 = row.get("rolling_mean_5", 0.0) or 0.0
            rolling_std_5 = row.get("rolling_std_5", 1.0) or 1.0
            macro_dxy = row.get("macro_dxy", 0.0) or 0.0
            macro_vix = row.get("macro_vix", 0.0) or 0.0
            macro_eia = row.get("macro_eia_inventory", 0.0) or 0.0

            # 交互项 1：汇率-油价联动
            new_row["interact_return_dxy"] = return_lag_1 * macro_dxy

            # 交互项 2：波动率-油价联动
            new_row["interact_return_vix"] = return_lag_1 * macro_vix

            # 交互项 3：波动调整因子（类 Sharpe）
            new_row["interact_sharpe_5"] = safe_divide(
                rolling_mean_5, rolling_std_5, fallback=0.0
            )

            # 交互项 4：供需动量
            new_row["interact_eia_momentum"] = macro_eia * return_lag_1

            enriched.append(new_row)

        logger.info(f"交互特征构造完成 rows={len(enriched)} 新增4个交互因子")
        return enriched
