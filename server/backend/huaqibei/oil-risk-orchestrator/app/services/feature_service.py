"""
特征工程服务

职责：
    - 编排 pipeline 层的各组件，完成完整特征构造流程
    - 输入：原始请求数据
    - 输出：可直接传入模型的标准特征矩阵（最后一行）

禁止：
    - 在此文件中导入 FastAPI
    - 在此文件中调用模型 API
"""

from app.pipeline.data_validator import DataValidator
from app.pipeline.asof_aligner import AsofAligner
from app.pipeline.lag_builder import LagBuilder
from app.pipeline.interaction_builder import InteractionBuilder
from app.schemas.request_schema import PredictRequest
from app.core.settings import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


class FeatureService:
    """
    特征工程服务。

    调用链：
        DataValidator → AsofAligner → LagBuilder → InteractionBuilder
    """

    def __init__(self) -> None:
        """初始化所有 pipeline 组件。"""
        self._validator = DataValidator(
            max_missing_ratio=settings.MAX_FEATURE_MISSING_RATIO
        )
        self._aligner = AsofAligner()
        self._lag_builder = LagBuilder()
        self._interaction_builder = InteractionBuilder()

    def build_feature_matrix(self, request: PredictRequest) -> dict:
        """
        执行完整特征构造流程。

        Args:
            request: 预测接口请求体。

        Returns:
            {
                "feature_vector": dict,   # 最新时间点的完整特征（传给模型）
                "current_price": float,   # 当前最新 close 价格
                "row_count": int,         # 参与计算的有效行数
            }

        Raises:
            ValueError: 数据校验失败时抛出，含详细错误信息。
        """
        # Step 1: 将请求数据转换为字典列表
        oil_records = [p.model_dump() for p in request.oil_data]

        # Step 2: 数据校验
        report = self._validator.validate_oil_data(oil_records)
        if not report.passed:
            error_msg = "; ".join(report.errors)
            logger.error(f"特征工程数据校验失败: {error_msg}")
            raise ValueError(f"数据校验失败: {error_msg}")

        # Step 3: 缺失值填充
        oil_records, repair_log = self._validator.fill_missing_values_with_log(oil_records)

        # Step 4: as-of 对齐宏观因子（若有）
        aligned_macro: dict | None = None
        if request.macro_factors:
            macro_records = [p.model_dump() for p in request.macro_factors]
            oil_dates = [r["date"] for r in oil_records]
            aligned_macro = self._aligner.align(oil_dates, macro_records)

        # Step 5: 滞后特征构造
        feature_rows = self._lag_builder.build_features(oil_records, aligned_macro)

        # Step 6: 交互特征构造
        feature_rows = self._interaction_builder.build_interactions(feature_rows)

        if not feature_rows:
            raise ValueError("特征构造后数据为空，请检查数据长度是否充足")

        # 取最后一行作为推理特征向量
        latest_row = feature_rows[-1]
        current_price = oil_records[-1]["close"]

        # 移除非特征字段
        exclude_fields = {"date", "close", "current_return"}
        feature_vector = {
            k: v for k, v in latest_row.items() if k not in exclude_fields
        }

        logger.info(
            f"特征构造完成 feature_count={len(feature_vector)} "
            f"current_price={current_price}"
        )

        return {
            "feature_vector": feature_vector,
            "current_price": current_price,
            "row_count": len(feature_rows),
            "missing_ratio": report.missing_ratio,
            "repair_log": repair_log,
        }
