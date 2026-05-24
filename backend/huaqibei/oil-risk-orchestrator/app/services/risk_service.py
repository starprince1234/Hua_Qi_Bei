"""
风险分级服务

职责：
    - 根据预测收益率与置信度计算风险等级
    - 输出 RiskAssessment 对象

禁止：
    - 在此文件中调用模型
    - 在此文件中生成报告文本
"""

from app.schemas.model_response_schema import ModelRawResponse
from app.schemas.prediction_schema import RiskAssessment
from app.core.constants import RiskLevel, TrendDirection
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class RiskService:
    """
    风险分级服务。

    分级逻辑：
        - |median| < LOW_THRESHOLD → LOW
        - LOW ≤ |median| < MEDIUM_THRESHOLD → MEDIUM
        - |median| ≥ MEDIUM_THRESHOLD → HIGH
        - |median| ≥ 2 × MEDIUM_THRESHOLD → EXTREME
    """

    def assess_risk(self, model_response: ModelRawResponse) -> RiskAssessment:
        """
        评估风险等级。

        Args:
            model_response: 云端模型原始响应。

        Returns:
            RiskAssessment 风险评估结果。
        """
        median = model_response.median
        abs_median = abs(median)
        confidence = self._compute_confidence(model_response)

        # 风险等级划分
        extreme_threshold = settings.RISK_MEDIUM_THRESHOLD * 2.0

        if abs_median >= extreme_threshold:
            level = RiskLevel.EXTREME
        elif abs_median >= settings.RISK_MEDIUM_THRESHOLD:
            level = RiskLevel.HIGH
        elif abs_median >= settings.RISK_LOW_THRESHOLD:
            level = RiskLevel.MEDIUM
        else:
            level = RiskLevel.LOW

        # 趋势方向
        if median > settings.RISK_LOW_THRESHOLD / 2:
            trend = TrendDirection.UP
            trend_display = "upward"
        elif median < -settings.RISK_LOW_THRESHOLD / 2:
            trend = TrendDirection.DOWN
            trend_display = "downward"
        else:
            trend = TrendDirection.FLAT
            trend_display = "sideways"

        # 风险信号文本
        signal = self._build_signal_text(level, trend, median, confidence)

        assessment = RiskAssessment(
            level=level,
            level_display=level.value.upper(),
            max_return_change=round(abs_median, 4),
            confidence_score=round(confidence, 3),
            trend=trend,
            trend_display=trend_display,
            signal=signal,
        )

        logger.info(
            f"风险评估完成 level={level.value} "
            f"trend={trend.value} "
            f"median_return={median:.4f}"
        )

        return assessment

    def _compute_confidence(self, model_response: ModelRawResponse) -> float:
        """
        用“区间宽度/中心收益”计算主置信度，并与模型原始置信度做加权融合。

        这样可以避免 mock 固定值导致的展示失真。
        """
        median = model_response.median
        interval_width = max(model_response.upper - model_response.lower, 1e-6)
        signal_scale = max(abs(median), 0.01)
        dispersion = interval_width / signal_scale

        derived_conf = 1.0 / (1.0 + dispersion)
        derived_conf = max(0.1, min(0.98, derived_conf))

        raw_conf = model_response.confidence_score
        if not (0.0 <= raw_conf <= 1.0):
            return round(derived_conf, 3)

        blended = 0.7 * derived_conf + 0.3 * raw_conf
        return round(max(0.1, min(0.98, blended)), 3)

    def _build_signal_text(
        self,
        level: RiskLevel,
        trend: TrendDirection,
        median: float,
        confidence: float,
    ) -> str:
        """
        构建风险信号摘要文本。

        Args:
            level: 风险等级。
            trend: 趋势方向。
            median: 预测收益率中位数。
            confidence: 模型置信度。

        Returns:
            自然语言风险信号。
        """
        pct = median * 100
        direction = "up" if pct > 0 else "down"
        return (
            f"Forecast indicates oil price moving {direction} by {abs(pct):.2f}%, "
            f"risk level {level.value.upper()}, with model confidence {confidence:.0%}."
        )
