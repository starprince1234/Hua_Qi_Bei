"""
请求入参 Schema

职责：
    - 定义所有 HTTP 请求的入参数据结构
    - 执行字段格式校验与约束
    - 提供清晰的字段文档

禁止：
    - 在此文件中写业务逻辑
    - 在此文件中执行推理
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional
from datetime import date


class OilDataPoint(BaseModel):
    """单条原始油价数据点。"""

    date: str = Field(..., description="日期，格式 YYYY-MM-DD")
    open: float = Field(..., description="开盘价 (USD)")
    high: float = Field(..., description="最高价 (USD)")
    low: float = Field(..., description="最低价 (USD)")
    close: float = Field(..., description="收盘价 (USD)")
    volume: Optional[float] = Field(None, description="成交量")

    @field_validator("open", "high", "low", "close")
    @classmethod
    def price_must_be_positive(cls, v: float) -> float:
        """价格必须为正数。"""
        if v <= 0:
            raise ValueError(f"价格必须 > 0，当前值: {v}")
        return v


class MacroFactorPoint(BaseModel):
    """单条宏观因子数据点（可扩展）。"""

    date: str = Field(..., description="日期，格式 YYYY-MM-DD")
    dxy: Optional[float] = Field(None, description="美元指数")
    vix: Optional[float] = Field(None, description="VIX 恐慌指数")
    sp500: Optional[float] = Field(None, description="S&P 500 指数")
    us_10y_yield: Optional[float] = Field(None, description="美国10年期国债收益率")
    eia_inventory: Optional[float] = Field(None, description="EIA 原油库存变化量 (万桶)")
    opec_output: Optional[float] = Field(None, description="OPEC 产量 (百万桶/天)")


class PredictRequest(BaseModel):
    """
    主预测接口请求体。

    输入：原始行情数据 + 宏观因子（可选）+ 预测配置
    """

    file_id: Optional[str] = Field(default=None, description="上传返回的 file_id")
    oil_data: Optional[list[OilDataPoint]] = Field(
        default=None,
        description="原油价格时间序列，调试场景可直接传入",
    )
    macro_factors: Optional[list[MacroFactorPoint]] = Field(
        None,
        description="宏观因子序列，可选，若提供则与油价对齐",
    )
    horizon: int = Field(
        default=5,
        ge=1,
        le=60,
        description="预测步数（天），范围 1-60",
    )
    target: str = Field(default="log_return", description="预测目标，仅支持 log_return")
    quantiles: list[float] = Field(
        default_factory=lambda: [0.05, 0.5, 0.95],
        min_length=2,
        description="返回分位数列表",
    )
    include_explainability: bool = Field(default=True, description="是否包含可解释性")
    include_knowledge_graph: bool = Field(default=True, description="是否包含知识图谱")
    include_report: bool = Field(default=True, description="是否包含结构化报告")
    report_style: str = Field(default="banking", description="报告风格: banking|concise|verbose")
    strict_mode: bool = Field(default=False, description="严格模式")

    # 兼容旧字段
    forecast_horizon: Optional[int] = Field(default=None, exclude=True)
    include_shap: Optional[bool] = Field(default=None, exclude=True)
    report_template: Optional[str] = Field(default=None, exclude=True)
    industries: Optional[list[str]] = Field(
        None,
        description="需要分析冲击的行业列表，不传则分析全部行业",
    )

    @field_validator("target")
    @classmethod
    def target_must_be_log_return(cls, value: str) -> str:
        if value != "log_return":
            raise ValueError("target 仅支持 log_return")
        return value

    @field_validator("quantiles")
    @classmethod
    def quantiles_must_be_valid(cls, value: list[float]) -> list[float]:
        if any(q < 0 or q > 1 for q in value):
            raise ValueError("quantiles 必须在 [0,1] 范围内")
        return value

    @model_validator(mode="after")
    def normalize_compat_fields(self) -> "PredictRequest":
        if self.forecast_horizon is not None:
            self.horizon = self.forecast_horizon
        if self.include_shap is not None:
            self.include_explainability = self.include_shap
        if self.report_template is not None:
            self.report_style = self.report_template
        if not self.oil_data and not self.file_id:
            raise ValueError("file_id 与 oil_data 至少提供一个")
        if self.oil_data and len(self.oil_data) < 30:
            raise ValueError("oil_data 至少需要 30 条")
        return self


class UploadCSVRequest(BaseModel):
    """CSV 上传请求元信息（文件通过 multipart 传入）。"""

    data_type: str = Field(
        ...,
        description="数据类型: oil_price | macro_factors",
    )
    date_column: str = Field(
        default="date",
        description="日期列名称",
    )
    encoding: str = Field(
        default="utf-8",
        description="文件编码",
    )
