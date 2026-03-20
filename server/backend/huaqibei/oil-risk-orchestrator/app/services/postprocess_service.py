"""
后处理服务

职责：
    - 将模型输出的收益率还原为价格路径
    - 构造逐步预测区间
    - 输出 PredictionResult

禁止：
    - 在此文件中调用模型
    - 在此文件中做风险分级（由 RiskService 负责）
"""

from app.schemas.model_response_schema import ModelRawResponse
from app.schemas.prediction_schema import PredictionResult, PredictionPoint, RiskAssessment
from app.core.constants import RiskLevel, TrendDirection
from app.utils.math_utils import restore_price_from_return
from app.core.logger import get_logger

logger = get_logger(__name__)


class PostprocessService:
    """
    后处理服务。

    职责：
        - 收益率 → 价格路径还原
        - 构造置信区间
        - 组装 PredictionResult（风险评估暂留空，由 RiskService 填充）
    """

    def restore_prediction_path(
        self,
        model_response: ModelRawResponse,
        current_price: float,
    ) -> list[PredictionPoint]:
        """
        将模型收益率预测还原为逐步价格路径。

        Args:
            model_response: 云端模型原始响应。
            current_price: 当前基准价格。

        Returns:
            逐步预测路径列表。
        """
        horizon = model_response.forecast_horizon
        median = model_response.median
        upper = model_response.upper
        lower = model_response.lower

        # 将单步收益率扩展到多步（简单线性路径近似）
        step_median = median / max(horizon, 1)
        step_upper = upper / max(horizon, 1)
        step_lower = lower / max(horizon, 1)

        median_prices = restore_price_from_return(
            current_price,
            [step_median] * horizon,
            use_log=True,
        )
        upper_prices = restore_price_from_return(
            current_price,
            [step_upper] * horizon,
            use_log=True,
        )
        lower_prices = restore_price_from_return(
            current_price,
            [step_lower] * horizon,
            use_log=True,
        )

        path = [
            PredictionPoint(
                step=i + 1,
                predicted_return=round(step_median * (i + 1), 6),
                predicted_price=median_prices[i],
                upper_price=upper_prices[i],
                lower_price=lower_prices[i],
            )
            for i in range(horizon)
        ]

        logger.info(
            f"价格路径还原完成 horizon={horizon} "
            f"base={current_price:.2f} "
            f"final_median={median_prices[-1]:.2f}"
        )

        return path

    def build_competition_multi_path(
        self,
        model_response: ModelRawResponse,
        current_price: float,
        full_path: list[PredictionPoint],
    ) -> list[PredictionPoint]:
        """
        构建比赛展示用固定多周期路径（1/3/7/14/30）。

        优先使用模型直接返回的多周期收益率；若无则从 full_path 采样。
        """
        competition_horizons = [1, 3, 7, 14, 30]

        # 优先：模型直出多周期点
        if model_response.multi_horizon_returns:
            horizon_to_point = {
                item.horizon: item for item in model_response.multi_horizon_returns
            }
            points: list[PredictionPoint] = []
            for h in competition_horizons:
                item = horizon_to_point.get(h)
                if not item:
                    continue
                points.append(
                    PredictionPoint(
                        step=h,
                        predicted_return=round(item.predicted_return, 6),
                        predicted_price=restore_price_from_return(current_price, [item.predicted_return], use_log=True)[0],
                        upper_price=restore_price_from_return(current_price, [item.upper_return], use_log=True)[0],
                        lower_price=restore_price_from_return(current_price, [item.lower_return], use_log=True)[0],
                    )
                )
            if points:
                return points

        # 回退：从 full_path 采样
        if not full_path:
            return []

        sampled: list[PredictionPoint] = []
        max_step = full_path[-1].step
        for h in competition_horizons:
            if h <= max_step:
                sampled.append(full_path[h - 1])
            else:
                sampled.append(full_path[-1])

        return sampled
