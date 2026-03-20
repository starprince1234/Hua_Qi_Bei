"""
后处理服务

职责：
    - 对模型输出做业务层后处理
    - 格式化、截断、归一化预测结果
    - 在模型输出异常时提供保底处理
"""

from typing import Any

from app.core.logger import get_logger
from app.schemas.prediction_schema import PredictionResult

logger = get_logger(__name__)


class PostprocessService:
    """
    预测结果后处理服务。
    """

    def postprocess(
        self,
        prediction: PredictionResult,
        max_price_bound: float | None = None,
        min_price_bound: float | None = None,
    ) -> PredictionResult:
        """
        对预测结果执行后处理。

        Args:
            prediction: 原始预测结果。
            max_price_bound: 价格上限（可选），超出则截断。
            min_price_bound: 价格下限（可选），低于则截断。

        Returns:
            后处理后的预测结果（不修改原始对象，返回新对象）。
        """
        # 价格边界截断
        if max_price_bound is not None or min_price_bound is not None:
            processed_path = []
            for point in prediction.prediction_path:
                price = point.predicted_price
                if max_price_bound is not None:
                    price = min(price, max_price_bound)
                if min_price_bound is not None:
                    price = max(price, min_price_bound)
                processed_path.append(point.model_copy(update={"predicted_price": round(price, 4)}))
            prediction = prediction.model_copy(update={"prediction_path": processed_path})

        # 置信度合法性保护
        score = prediction.risk_assessment.confidence_score
        if not (0.0 <= score <= 1.0):
            clamped = max(0.0, min(1.0, score))
            logger.warning(f"PostprocessService: 置信度 {score} 超出范围，截断为 {clamped}")
            new_risk = prediction.risk_assessment.model_copy(
                update={"confidence_score": clamped}
            )
            prediction = prediction.model_copy(update={"risk_assessment": new_risk})

        return prediction

    def format_for_response(self, prediction: PredictionResult) -> dict[str, Any]:
        """
        将 PredictionResult 转换为 API 响应字典。

        Returns:
            可 JSON 序列化的字典。
        """
        return prediction.model_dump(mode="json")
