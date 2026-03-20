"""
报告输出 Schema

职责：
    - 定义 LLM 生成报告的最终输出结构
    - 定义统一 API 响应包装格式
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, Any
from datetime import datetime
from app.schemas.prediction_schema import PredictionResult
from app.schemas.industry_schema import IndustryImpactResult


class RepairLogItem(BaseModel):
    field: str = Field(..., description="修复字段")
    strategy: str = Field(..., description="修复策略")
    count: int = Field(..., description="修复数量")
    severity: str = Field(default="warning", description="严重级别")
    before_after_sample: Optional[dict[str, Any]] = Field(
        default=None,
        description="修复前后摘要样本",
    )


class AsofAlignment(BaseModel):
    enabled: bool = False
    dropped_rows: int = 0
    reason: str = ""


class DataProcessingLog(BaseModel):
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    repairs: list[RepairLogItem] = Field(default_factory=list)
    asof_alignment: AsofAlignment = Field(default_factory=AsofAlignment)
    repair_log: list[RepairLogItem] = Field(default_factory=list, exclude=True)

    @model_validator(mode="after")
    def normalize_repair_log(self) -> "DataProcessingLog":
        if self.repair_log and not self.repairs:
            self.repairs = self.repair_log
        return self


class ReasonTagStat(BaseModel):
    tag: str
    count: int


class SelectedFactorsReasonSummary(BaseModel):
    selected_count: int = 0
    dropped_count: int = 0
    matched_top_factors: list[str] = Field(default_factory=list)
    top_reason_tags: list[ReasonTagStat] = Field(default_factory=list)


class LLMContextPack(BaseModel):
    prediction: dict[str, Any]
    risk_analysis: dict[str, Any]
    top_drivers: list[dict[str, Any]]
    industry_impact: list[dict[str, Any]]
    knowledge_graph_paths: list[dict[str, Any]]


class ConstrainedReportOutput(BaseModel):
    summary_conclusion: str
    trend_and_confidence: str
    key_drivers: str
    industry_signals: str
    risks_and_limitations: str


class FactorContribution(BaseModel):
    """单个因子的解释贡献条目。"""

    factor_name: str = Field(..., description="因子名称")
    factor_name_cn: str = Field(..., description="因子中文名")
    shap_value: float = Field(..., description="SHAP 贡献值")
    direction: str = Field(..., description="方向: 正向/负向")
    description: str = Field(default="", description="因子解释文本")


class ExplainabilitySection(BaseModel):
    """可解释性分析章节。"""

    top_factors: list[FactorContribution] = Field(
        default_factory=list,
        description="Top 因子贡献列表（按绝对值降序）",
    )
    knowledge_graph_narrative: str = Field(
        default="",
        description="知识图谱传导路径叙述",
    )
    summary: str = Field(default="", description="解释层综合摘要")


class RiskReport(BaseModel):
    """
    完整智能风险报告。

    由 LLM 生成的全量报告，包含：
    - 预测摘要
    - 可解释性分析
    - 行业冲击
    - 操作建议
    """

    report_id: str = Field(..., description="报告唯一 ID")
    generated_at: str = Field(..., description="生成时间 ISO8601")
    template: str = Field(..., description="报告模板类型")

    # 各分析章节
    prediction: PredictionResult = Field(..., description="预测结果")
    explainability: ExplainabilitySection = Field(..., description="可解释性分析")
    industry_impact: IndustryImpactResult = Field(..., description="行业冲击分析")
    data_processing_log: Optional[DataProcessingLog] = Field(
        default=None,
        description="数据处理日志",
    )
    knowledge_graph_path: list[dict[str, Any]] = Field(
        default_factory=list,
        description="知识图谱关键路径",
    )
    selected_factors_reason_summary: Optional[SelectedFactorsReasonSummary] = Field(
        default=None,
        description="统计筛选理由摘要",
    )
    constrained_report: Optional[ConstrainedReportOutput] = Field(
        default=None,
        description="受约束报告章节输出",
    )
    llm_provenance: dict[str, Any] = Field(
        default_factory=dict,
        description="LLM 调用与校验元数据",
    )

    # LLM 自然语言报告正文
    executive_summary: str = Field(default="", description="管理层摘要（LLM生成）")
    detailed_analysis: str = Field(default="", description="详细分析（LLM生成）")
    risk_advice: str = Field(default="", description="风险建议（LLM生成）")


class APIResponse(BaseModel):
    """统一 API 响应包装格式。"""

    success: bool = Field(..., description="是否成功")
    code: int = Field(..., description="业务状态码")
    message: str = Field(default="", description="状态消息")
    data: Optional[Any] = Field(None, description="业务数据")
    request_id: Optional[str] = Field(None, description="请求追踪 ID")

    @classmethod
    def ok(cls, data: Any = None, message: str = "success") -> "APIResponse":
        """构建成功响应。"""
        return cls(success=True, code=200, message=message, data=data)

    @classmethod
    def error(cls, code: int, message: str) -> "APIResponse":
        """构建错误响应。"""
        return cls(success=False, code=code, message=message, data=None)


class ErrorResponse(BaseModel):
    success: bool = Field(default=False)
    code: int = Field(..., description="HTTP状态码")
    message: str = Field(..., description="错误信息")
    details: Optional[Any] = Field(default=None, description="错误详情")
    request_id: str = Field(..., description="请求追踪ID")


class ReturnQuantilePoint(BaseModel):
    t: int
    q05: float
    q50: float
    q95: float


class PredictionSummaryV1(BaseModel):
    horizon: int
    return_quantiles: dict[str, float] = Field(default_factory=dict)
    confidence_score: float
    risk_level: str
    model_version: str
    feature_config_version: str = "v1"
    scaler_version: str = "v1"


class FuturePathStep(BaseModel):
    step: int
    median_price: float
    upper_price: float
    lower_price: float
    predicted_return: Optional[float] = None
    upper_return: Optional[float] = None
    lower_return: Optional[float] = None


class FuturePathBlock(BaseModel):
    steps: list[FuturePathStep] = Field(default_factory=list)


class ShockIndustryItem(BaseModel):
    industry: str
    direction: str
    magnitude: float


class ShockSignal(BaseModel):
    overall_intensity: float
    alert_level: str
    top_affected_industries: list[ShockIndustryItem] = Field(default_factory=list)


class FactorContributionV1(BaseModel):
    factor: str
    contribution: float


class ExplainabilityBlock(BaseModel):
    top_factors: list[FactorContributionV1] = Field(default_factory=list)
    method: str = "shap_or_proxy"


class KGPath(BaseModel):
    industry: str
    path_nodes: list[str] = Field(default_factory=list)
    path_labels: list[str] = Field(default_factory=list)
    arrow_path: str
    node_levels: list[dict[str, str]] = Field(default_factory=list)


class KnowledgeGraphBlock(BaseModel):
    paths: list[KGPath] = Field(default_factory=list)


class AIRiskInsight(BaseModel):
    risk_level: str = "LOW"
    detail: str = ""
    model_id: str = ""


class AIIndustryInsight(BaseModel):
    detail: str = ""
    model_id: str = ""


class AIKnowledgeGraphInsight(BaseModel):
    detail: str = ""
    model_id: str = ""


class AIReportInsight(BaseModel):
    detail: str = ""
    model_id: str = ""


class AIInsightsBlock(BaseModel):
    risk: AIRiskInsight
    industry: AIIndustryInsight
    knowledge_graph: AIKnowledgeGraphInsight
    report: AIReportInsight


class FactorReasonItem(BaseModel):
    factor: str
    reason_tag: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class FactorSelectionReasons(BaseModel):
    selected: list[FactorReasonItem] = Field(default_factory=list)
    rejected: list[FactorReasonItem] = Field(default_factory=list)


class DataProcessingLogV1(BaseModel):
    validation_passed: bool
    repair_actions: list[dict[str, Any]] = Field(default_factory=list)
    asof_alignment: bool
    lag_features_built: bool


class IndustryReportItem(BaseModel):
    industry: str
    risk_point: str
    reason: str
    action: str


class RiskReportSections(BaseModel):
    executive_summary: str
    trend_and_confidence: str
    key_drivers: str
    industry_impacts: str
    risks_and_limits: str


class ReportResult(BaseModel):
    report_id: str
    schema_version: str = "risk_report_v1"
    sections: RiskReportSections
    provenance: dict[str, Any] = Field(default_factory=dict)


class PredictResultPayload(BaseModel):
    prediction: PredictionSummaryV1
    future_path: FuturePathBlock
    shock_signal: ShockSignal
    explainability: ExplainabilityBlock
    knowledge_graph: KnowledgeGraphBlock
    ai_insights: AIInsightsBlock
    factor_selection_reasons: FactorSelectionReasons
    report: ReportResult
    data_processing_log: DataProcessingLogV1


class IndustryImpactItemV1(BaseModel):
    industry: str
    direction: str
    magnitude: float
