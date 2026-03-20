"""
风险评估服务

职责：
    - 将模型原始响应转化为结构化风险评估与预测路径
    - 计算置信区间、趋势判断、风险等级
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.logger import get_logger
from app.schemas.model_response_schema import ModelRawResponse
from app.schemas.prediction_schema import (
    PredictionPathPoint,
    PredictionResult,
    RiskAssessment,
    RiskLevel,
)

logger = get_logger(__name__)


class RiskService:
    """
    风险评估服务。

    将模型原始响应（ModelRawResponse）转化为完整的 PredictionResult。
    """

    def build_prediction_result(
        self,
        model_response: ModelRawResponse,
        current_price: float,
        forecast_horizon: int,
        shap_top_features: list[dict[str, Any]] | None = None,
    ) -> PredictionResult:
        """
        构建完整预测结果。

        Args:
            model_response: 模型原始响应。
            current_price: 当前价格（美元/桶）。
            forecast_horizon: 预测步数（天）。
            shap_top_features: Top SHAP 贡献特征列表。

        Returns:
            PredictionResult 完整预测结果。
        """
        # 构建预测路径
        prediction_path = self._build_prediction_path(
            model_response=model_response,
            current_price=current_price,
            forecast_horizon=forecast_horizon,
        )

        # 风险评估
        risk_assessment = self._assess_risk(
            model_response=model_response,
            prediction_path=prediction_path,
        )

        return PredictionResult(
            prediction_id=str(uuid.uuid4()),
            current_price=round(current_price, 4),
            forecast_horizon=forecast_horizon,
            prediction_path=prediction_path,
            risk_assessment=risk_assessment,
            shap_top_features=shap_top_features or [],
            model_version=model_response.model_version,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _build_prediction_path(
        self,
        model_response: ModelRawResponse,
        current_price: float,
        forecast_horizon: int,
    ) -> list[PredictionPathPoint]:
        """构建逐步预测路径。"""
        path: list[PredictionPathPoint] = []

        # 如果模型返回了多步预测序列，优先使用
        if model_response.multi_horizon_returns:
            for mh in model_response.multi_horizon_returns:
                predicted_price = current_price * (1 + mh.predicted_return)
                upper_price = (
                    current_price * (1 + mh.upper) if mh.upper is not None else None
                )
                lower_price = (
                    current_price * (1 + mh.lower) if mh.lower is not None else None
                )
                path.append(
                    PredictionPathPoint(
                        day=mh.horizon,
                        predicted_price=round(predicted_price, 4),
                        predicted_return=round(mh.predicted_return, 6),
                        upper_price=round(upper_price, 4) if upper_price else None,
                        lower_price=round(lower_price, 4) if lower_price else None,
                    )
                )
            return path

        # 否则从单步预测插值生成路径
        median = model_response.median
        upper = model_response.upper
        lower = model_response.lower

        for day in range(1, forecast_horizon + 1):
            ratio = day / forecast_horizon
            step_return = median * ratio
            step_upper = upper * ratio
            step_lower = lower * ratio
            path.append(
                PredictionPathPoint(
                    day=day,
                    predicted_price=round(current_price * (1 + step_return), 4),
                    predicted_return=round(step_return, 6),
                    upper_price=round(current_price * (1 + step_upper), 4),
                    lower_price=round(current_price * (1 + step_lower), 4),
                )
            )

        return path

    def _assess_risk(
        self,
        model_response: ModelRawResponse,
        prediction_path: list[PredictionPathPoint],
    ) -> RiskAssessment:
        """评估风险等级与趋势。"""
        from app.core.constants import (
            RISK_LOW_THRESHOLD,
            RISK_HIGH_THRESHOLD,
            RISK_EXTREME_THRESHOLD,
        )

        max_return_change = abs(model_response.median)

        if max_return_change < RISK_LOW_THRESHOLD:
            level = RiskLevel.LOW
        elif max_return_change < RISK_HIGH_THRESHOLD:
            level = RiskLevel.MEDIUM
        elif max_return_change < RISK_EXTREME_THRESHOLD:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.EXTREME

        # 趋势判断
        if model_response.median > 0.005:
            trend_display = "上涨"
        elif model_response.median < -0.005:
            trend_display = "下跌"
        else:
            trend_display = "震荡"

        # 预测路径波动率
        if len(prediction_path) >= 2:
            returns = [p.predicted_return for p in prediction_path]
            mean_r = sum(returns) / len(returns)
            variance = sum((r - mean_r) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance)
        else:
            volatility = 0.0

        return RiskAssessment(
            level=level,
            trend_display=trend_display,
            max_return_change=round(max_return_change, 6),
            confidence_score=round(model_response.confidence_score, 4),
            volatility=round(volatility, 6),
        )
