"""
特征工程服务

职责：
    - 将原始油价记录转化为模型可用的特征向量
    - 编排 Pipeline（LagBuilder → InteractionBuilder → DataValidator）
"""

from typing import Any

from app.core.logger import get_logger
from app.pipeline.data_validator import DataValidator
from app.pipeline.lag_builder import LagBuilder
from app.pipeline.interaction_builder import InteractionBuilder
from app.pipeline.asof_aligner import AsofAligner

logger = get_logger(__name__)


class FeatureService:
    """
    特征工程服务。

    负责将原始数据记录转化为模型所需的特征字典。
    """

    def __init__(self) -> None:
        self._validator = DataValidator()
        self._lag_builder = LagBuilder()
        self._interaction_builder = InteractionBuilder()
        self._aligner = AsofAligner()

    def build_feature_vector(
        self,
        records: list[dict[str, Any]],
        forecast_horizon: int = 7,
    ) -> dict[str, Any]:
        """
        从历史记录中构建最新一行的特征向量。

        Args:
            records: 原始油价时序记录列表（按时间升序）。
            forecast_horizon: 预测步数（天）。

        Returns:
            特征字典，用于传递给模型服务。
        """
        # 数据校验
        report = self._validator.validate_oil_data(records)
        if not report.passed:
            logger.warning(f"特征工程：数据校验警告 errors={report.errors}")

        # 缺失值填充
        filled = self._validator.fill_missing_values(records)

        # 添加滞后特征
        with_lags = self._lag_builder.build(filled)

        # 添加交叉特征
        with_interactions = self._interaction_builder.build(with_lags)

        # 取最新一行作为特征向量
        if not with_interactions:
            return {"forecast_horizon": forecast_horizon}

        latest = dict(with_interactions[-1])
        latest["forecast_horizon"] = forecast_horizon

        logger.debug(f"FeatureService: 特征向量包含 {len(latest)} 个字段")
        return latest

    def build_feature_sequence(
        self,
        records: list[dict[str, Any]],
        forecast_horizon: int = 7,
    ) -> list[dict[str, Any]]:
        """
        构建完整特征序列（用于多步预测或批量推理）。

        Args:
            records: 原始油价时序记录列表。
            forecast_horizon: 预测步数。

        Returns:
            特征序列列表。
        """
        filled = self._validator.fill_missing_values(records)
        with_lags = self._lag_builder.build(filled)
        with_interactions = self._interaction_builder.build(with_lags)

        for rec in with_interactions:
            rec["forecast_horizon"] = forecast_horizon

        return with_interactions
