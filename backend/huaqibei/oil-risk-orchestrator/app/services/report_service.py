"""
报告生成服务

职责：
    - 调用 LLM API 生成自然语言风险报告
    - 有 LLM API Key 时调用真实 API
    - 无 API Key 时使用规则模板生成报告
    - 组装最终 RiskReport

禁止：
    - 在此文件中做预测计算
    - 在此文件中做特征工程
"""

import asyncio
import re
import time
from datetime import datetime
from typing import Optional, Any

from openai import OpenAI, APIStatusError, AuthenticationError, RateLimitError, APITimeoutError

from app.schemas.prediction_schema import PredictionResult
from app.schemas.industry_schema import IndustryImpactResult
from app.schemas.report_schema import (
    RiskReport,
    ExplainabilitySection,
    DataProcessingLog,
    SelectedFactorsReasonSummary,
    LLMContextPack,
    ConstrainedReportOutput,
    ReportResult,
    RiskReportSections,
    IndustryReportItem,
)
from app.core.settings import settings
from app.core.constants import RiskLevel
from app.utils.json_utils import generate_request_id
from app.utils.json_utils import safe_json_dumps, safe_json_loads
from app.core.logger import get_logger

logger = get_logger(__name__)


class _LLMCallError(Exception):
    """LLM 调用失败（用于触发模板降级）。"""


class ReportService:
    """
    报告生成服务。

    流程：
        1. 若有 LLM API Key → 调用 LLM 生成自然语言报告
        2. 否则 → 规则模板填充
        3. 组装并返回完整 RiskReport
    """

    _REPORT_STORE: dict[str, RiskReport] = {}

    def __init__(self) -> None:
        self._last_llm_meta: dict[str, Any] = {}
        self._llm_retry_mode: bool = False

    async def generate_report(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        explainability: ExplainabilitySection,
        template: str = "standard",
        data_processing_log: DataProcessingLog | None = None,
        selected_factors_reason_summary: SelectedFactorsReasonSummary | None = None,
        knowledge_graph_path: list[dict] | None = None,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> RiskReport:
        """
        生成完整智能风险报告。

        Args:
            prediction: 预测结果。
            industry_impact: 行业冲击分析结果。
            explainability: 可解释性分析章节。
            template: 报告模板类型。

        Returns:
            RiskReport 完整报告对象。
        """
        report_id = generate_request_id()
        context_pack = self.build_context_pack(
            prediction=prediction,
            industry_impact=industry_impact,
            explainability=explainability,
        )

        provenance: dict[str, Any] = {
            "generation_mode": "template_fallback",
            "provider": settings.LLM_PROVIDER,
            "model_id": settings.LLM_MODEL_ID,
            "latency_ms": 0,
            "schema_validated": True,
            "request_id": None,
            "usage": None,
        }

        constrained: Optional[ConstrainedReportOutput] = None

        if settings.LLM_API_KEY.strip():
            logger.info("使用 LLM API 生成报告")
            constrained = await self._generate_constrained_report(
                context_pack,
                model_id=model_id,
                system_prompt=system_prompt,
            )
            if constrained is not None:
                provenance.update(
                    {
                        "generation_mode": "llm",
                        "latency_ms": self._last_llm_meta.get("latency_ms", 0),
                        "schema_validated": True,
                        "request_id": self._last_llm_meta.get("request_id"),
                        "usage": self._last_llm_meta.get("usage"),
                        "model_id": self._last_llm_meta.get("model_id", settings.LLM_MODEL_ID),
                    }
                )
                executive = constrained.summary_conclusion
                detailed = (
                    constrained.trend_and_confidence
                    + " "
                    + constrained.key_drivers
                    + " "
                    + constrained.industry_signals
                )
                advice = constrained.risks_and_limitations
            else:
                logger.warning("LLM 返回未通过约束校验，降级为模板报告")
                executive, detailed, advice = self._rule_based_report(
                    prediction, industry_impact, explainability
                )
                constrained = self._build_constrained_from_rule(executive, detailed, advice)
        else:
            logger.warning("LLM_API_KEY 未配置，使用规则模板生成报告")
            executive, detailed, advice = self._rule_based_report(
                prediction, industry_impact, explainability
            )
            constrained = self._build_constrained_from_rule(executive, detailed, advice)

        executive = self._ensure_english_summary(executive, prediction)
        detailed = self._ensure_english_detailed(
            detailed,
            prediction,
            industry_impact,
            explainability,
        )
        advice = self._ensure_english_advice(advice, prediction)
        if constrained is not None:
            constrained.summary_conclusion = self._ensure_english_summary(
                constrained.summary_conclusion,
                prediction,
            )

        report = RiskReport(
            report_id=report_id,
            generated_at=datetime.utcnow().isoformat() + "Z",
            template=template,
            prediction=prediction,
            explainability=explainability,
            industry_impact=industry_impact,
            data_processing_log=data_processing_log,
            knowledge_graph_path=knowledge_graph_path or [],
            selected_factors_reason_summary=selected_factors_reason_summary,
            constrained_report=constrained,
            llm_provenance=provenance,
            executive_summary=executive,
            detailed_analysis=detailed,
            risk_advice=advice,
        )
        self._REPORT_STORE[report_id] = report
        return report

    def to_report_result(self, report: RiskReport) -> ReportResult:
        industry_items = []
        for impact in report.industry_impact.impacts:
            industry_items.append(
                IndustryReportItem(
                    industry=impact.industry,
                    risk_point=f"{impact.impact_direction.value}:{impact.impact_magnitude:.2f}",
                    reason=impact.narrative,
                    action=(
                        "Enhance risk hedging" if impact.impact_magnitude >= 0.5 else "Maintain routine monitoring"
                    ),
                )
            )

        industry_summary = "；".join(
            [
                f"{item.industry}:{item.risk_point}:{item.reason}"
                for item in industry_items
            ]
        )

        sections = RiskReportSections(
            executive_summary=self._ensure_english_summary(report.executive_summary, report.prediction),
            trend_and_confidence=(
                report.constrained_report.trend_and_confidence
                if report.constrained_report
                else report.detailed_analysis[:180]
            ),
            key_drivers=(
                report.constrained_report.key_drivers
                if report.constrained_report
                else report.detailed_analysis[:180]
            ),
            industry_impacts=industry_summary,
            risks_and_limits=(
                report.constrained_report.risks_and_limitations
                if report.constrained_report
                else report.risk_advice
            ),
        )

        provenance = report.llm_provenance or {}
        return ReportResult(
            report_id=report.report_id,
            schema_version="risk_report_v1",
            sections=sections,
            provenance={
                "generation_mode": provenance.get("generation_mode", "template_fallback"),
                "provider": provenance.get("provider", settings.LLM_PROVIDER),
                "model_id": provenance.get("model_id", settings.LLM_MODEL_ID),
                "latency_ms": provenance.get("latency_ms", 0),
                "schema_validated": provenance.get("schema_validated", False),
                "request_id": provenance.get("request_id"),
                "usage": provenance.get("usage"),
                "template": report.template,
            },
        )

    def get_report_result(self, report_id: str) -> Optional[ReportResult]:
        report = self._REPORT_STORE.get(report_id)
        if report is None:
            return None
        return self.to_report_result(report)

    def get_report(self, report_id: str) -> Optional[RiskReport]:
        return self._REPORT_STORE.get(report_id)

    def build_context_pack(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        explainability: ExplainabilitySection,
    ) -> LLMContextPack:
        kg_paths = []
        for impact in industry_impact.impacts[:5]:
            kg_paths.append(
                {
                    "industry": impact.industry,
                    "path": impact.transmission_path,
                    "narrative": impact.narrative,
                }
            )

        top_drivers = [
            {
                "factor_name": item.factor_name,
                "factor_name_cn": item.factor_name_cn,
                "impact": item.shap_value,
                "direction": item.direction,
            }
            for item in explainability.top_factors[:8]
        ]

        return LLMContextPack(
            prediction={
                "current_price": prediction.current_price,
                "forecast_horizon": prediction.forecast_horizon,
                "final_price": prediction.prediction_path[-1].predicted_price,
            },
            risk_analysis={
                "risk_level": prediction.risk_assessment.level_display,
                "trend": prediction.risk_assessment.trend_display,
                "confidence_score": prediction.risk_assessment.confidence_score,
                "max_return_change": prediction.risk_assessment.max_return_change,
            },
            top_drivers=top_drivers,
            industry_impact=[
                {
                    "industry": impact.industry,
                    "industry_name_cn": impact.industry_name_cn,
                    "impact_direction": impact.impact_direction.value,
                    "impact_magnitude": impact.impact_magnitude,
                }
                for impact in industry_impact.impacts
            ],
            knowledge_graph_paths=kg_paths,
        )

    async def _generate_constrained_report(
        self,
        context_pack: LLMContextPack,
        model_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> Optional[ConstrainedReportOutput]:
        context_dict = self._filter_context_whitelist(context_pack)
        messages = self._build_messages(context_dict, system_prompt=system_prompt)

        self._llm_retry_mode = False
        try:
            raw = await self.call_llm(
                messages=messages,
                json_mode=settings.LLM_JSON_MODE,
                model_id=model_id,
            )
            parsed = self._parse_and_validate_report_output(raw)
            if parsed is not None and self._validate_llm_output_fields(parsed, context_pack):
                return parsed
        except _LLMCallError as err:
            logger.warning(f"LLM 首次调用失败: {err}")

        retry_messages = messages + [
            {
                "role": "system",
                "content": "上一轮输出未通过校验。请仅输出严格 JSON，禁止附加解释。",
            }
        ]
        self._llm_retry_mode = True
        try:
            raw_retry = await self.call_llm(
                messages=retry_messages,
                json_mode=False,
                model_id=model_id,
            )
            parsed_retry = self._parse_and_validate_report_output(raw_retry)
            if parsed_retry is not None and self._validate_llm_output_fields(parsed_retry, context_pack):
                return parsed_retry
        except _LLMCallError as err:
            logger.warning(f"LLM 二次调用失败: {err}")
        finally:
            self._llm_retry_mode = False

        return None

    async def call_llm(
        self,
        messages: list[dict[str, str]],
        json_mode: bool,
        model_id: Optional[str] = None,
    ) -> str:
        """
        统一 LLM 调用函数。

        - Provider: OpenAI / 讯飞 MaaS OpenAI 兼容
        - 失败策略: 401/403 立即失败；429/500/503 重试一次
        """
        if not settings.LLM_API_KEY.strip():
            raise _LLMCallError("LLM_API_KEY 未配置")

        client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )
        chosen_model_id = model_id or settings.LLM_MODEL_ID
        max_attempts = max(1, settings.LLM_MAX_RETRIES)
        last_exception: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            start = time.perf_counter()
            try:
                extra_headers: dict[str, str] = {}
                extra_body: dict[str, Any] = {}

                provider = (settings.LLM_PROVIDER or "").lower()
                if provider == "xf_maas":
                    extra_headers = {"lora_id": settings.LLM_LORA_ID or "0"}
                    extra_body["search_disable"] = settings.LLM_SEARCH_DISABLE
                elif provider == "siliconflow":
                    extra_body.update(
                        {
                            "enable_thinking": settings.LLM_ENABLE_THINKING,
                            "thinking_budget": settings.LLM_THINKING_BUDGET,
                            "top_k": settings.LLM_TOP_K,
                        }
                    )
                if json_mode and self._supports_json_mode(chosen_model_id):
                    extra_body["response_format"] = {"type": "json_object"}

                temperature = 0 if self._llm_retry_mode else settings.LLM_TEMPERATURE
                max_tokens = settings.LLM_MAX_TOKENS + (200 if self._llm_retry_mode else 0)

                response = await asyncio.to_thread(
                    client.chat.completions.create,
                    model=chosen_model_id,
                    messages=messages,
                    temperature=temperature,
                    top_p=settings.LLM_TOP_P,
                    frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
                    max_tokens=max_tokens,
                    stream=False,
                    extra_headers=extra_headers,
                    extra_body=extra_body,
                )

                latency_ms = int((time.perf_counter() - start) * 1000)
                usage = response.usage.model_dump() if getattr(response, "usage", None) else None
                self._last_llm_meta = {
                    "provider": settings.LLM_PROVIDER,
                    "model_id": chosen_model_id,
                    "latency_ms": latency_ms,
                    "request_id": getattr(response, "_request_id", None),
                    "usage": usage,
                }

                content = ""
                if response.choices and response.choices[0].message:
                    content = response.choices[0].message.content or ""
                if not content.strip():
                    raise _LLMCallError("LLM 返回内容为空")
                return content

            except AuthenticationError as err:
                raise _LLMCallError(f"LLM 鉴权失败: {err}") from err
            except APITimeoutError as err:
                raise _LLMCallError(f"LLM 调用超时({settings.LLM_TIMEOUT}s): {err}") from err
            except RateLimitError as err:
                last_exception = err
                if attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise _LLMCallError(f"LLM 限流: {err}") from err
            except APIStatusError as err:
                last_exception = err
                status = getattr(err, "status_code", None)
                if status in (401, 403):
                    raise _LLMCallError(f"LLM 权限错误 status={status}") from err
                if status in (429, 500, 503) and attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise _LLMCallError(f"LLM 状态错误 status={status}") from err
            except Exception as err:
                last_exception = err
                if attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise _LLMCallError(f"LLM 调用异常: {err}") from err

        raise _LLMCallError(f"LLM 调用失败: {last_exception}")

    def _supports_json_mode(self, model_id: str) -> bool:
        normalized = (model_id or "").lower()
        return ("deepseek" in normalized and "r1" in normalized) or (
            "deepseek" in normalized and "v3" in normalized
        )

    def _build_messages(
        self,
        context_dict: dict[str, Any],
        system_prompt: Optional[str] = None,
    ) -> list[dict[str, str]]:
        user_payload = {
            "task": "Generate a bank-grade risk report JSON based on context_pack with actionable and auditable conclusions.",
            "schema_keys": [
                "summary_conclusion",
                "trend_and_confidence",
                "key_drivers",
                "industry_signals",
                "risks_and_limitations",
            ],
            "constraints": [
                "Use facts only from context_pack",
                "Do not output any keys outside schema_keys",
                "Output must be a JSON object",
                "Each field should be concise and evidence-based",
                "Include quantitative signals (at least two among horizon, price, confidence)",
                "Language must be English",
            ],
            "context_pack": context_dict,
        }
        return [
            {
                "role": "system",
                "content": (
                    (system_prompt or "You are an enterprise banking risk analysis assistant.")
                    +
                    "Output strict JSON with the provided schema keys and no markdown. "
                    "Use professional English, conclusion first, then evidence."
                ),
            },
            {
                "role": "user",
                "content": safe_json_dumps(user_payload),
            },
        ]

    def _build_prompt(self, context_dict: dict) -> str:
        return (
            "请基于以下 Context Pack 生成受约束 JSON 报告。"
            "禁止引用 Context Pack 之外的实体、数字和事件。\n"
            "Context Pack:\n"
            f"{safe_json_dumps(context_dict, indent=2)}\n"
            "输出 JSON 键必须严格为："
            "summary_conclusion,trend_and_confidence,key_drivers,industry_signals,risks_and_limitations"
        )

    def _filter_context_whitelist(self, pack: LLMContextPack) -> dict:
        return {
            "prediction": pack.prediction,
            "risk_analysis": pack.risk_analysis,
            "top_drivers": pack.top_drivers,
            "industry_impact": pack.industry_impact,
            "knowledge_graph_paths": pack.knowledge_graph_paths,
        }

    def _parse_and_validate_report_output(self, text: str) -> Optional[ConstrainedReportOutput]:
        body = text.strip()
        if "```" in body:
            match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", body)
            if match:
                body = match.group(1)
        try:
            payload = safe_json_loads(body)
            return ConstrainedReportOutput(**payload)
        except Exception:
            return None

    def _validate_llm_output_fields(
        self,
        output: ConstrainedReportOutput,
        pack: LLMContextPack,
    ) -> bool:
        text = " ".join(
            [
                output.summary_conclusion,
                output.trend_and_confidence,
                output.key_drivers,
                output.industry_signals,
                output.risks_and_limitations,
            ]
        )

        allowed_factors = set()
        for item in pack.top_drivers:
            allowed_factors.add(item.get("factor_name_cn", ""))
            allowed_factors.add(item.get("factor_name", ""))

        allowed_industries = set()
        for item in pack.industry_impact:
            allowed_industries.add(item.get("industry_name_cn", ""))
            allowed_industries.add(item.get("industry", ""))

        factor_hits = [name for name in allowed_factors if name and name in text]
        industry_hits = [name for name in allowed_industries if name and name in text]

        if not factor_hits:
            return False
        if not industry_hits:
            return False

        if "external news" in text.lower() or "internet" in text.lower() or "reported" in text.lower():
            return False

        # 至少包含一个可审计的量化信号
        if not any(token in text for token in ["%", "$", "confidence", "horizon", "price"]):
            return False

        return True

    def _build_constrained_from_rule(
        self,
        executive: str,
        detailed: str,
        advice: str,
    ) -> ConstrainedReportOutput:
        return ConstrainedReportOutput(
            summary_conclusion=executive,
            trend_and_confidence=detailed[:200],
            key_drivers=detailed[:200],
            industry_signals=detailed[:200],
            risks_and_limitations=advice,
        )

    def _rule_based_report(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        explainability: ExplainabilitySection,
    ) -> tuple[str, str, str]:
        """
        规则模板报告（LLM 不可用时的降级方案）。

        Args:
            prediction: 预测结果。
            industry_impact: 行业冲击结果。
            explainability: 解释性章节。

        Returns:
            (executive_summary, detailed_analysis, risk_advice) 三元组。
        """
        risk = prediction.risk_assessment
        top_factors = [f.factor_name for f in explainability.top_factors[:3]]
        high_alert = industry_impact.high_alert_industries
        final_price = prediction.prediction_path[-1].predicted_price

        executive = (
            f"The model forecasts oil price over the next {prediction.forecast_horizon} days to "
            f"{risk.trend_display} toward approximately ${final_price:.2f}, with a return swing of "
            f"{risk.max_return_change*100:.2f}%, risk level {risk.level_display}, and confidence {risk.confidence_score:.0%}."
        )

        factor_str = ", ".join(top_factors) if top_factors else "short-term momentum"
        alert_str = (
            f"High-alert industries include: {', '.join(high_alert)}." if high_alert else ""
        )
        detailed = (
            f"This forecast is primarily driven by {factor_str}. "
            f"Oil price is expected to move from ${prediction.current_price:.2f} "
            f"to ${final_price:.2f} under a {risk.trend_display} scenario. "
            "Key assumptions are based on model-derived factor contributions and cross-industry transmission mapping. "
            f"{alert_str}"
        )

        if risk.level in (RiskLevel.HIGH, RiskLevel.EXTREME):
            advice = (
                "1. Hedge oil-sensitive exposures with futures/options to lock cost levels; "
                "2. Recalibrate credit limits for highly sensitive sectors such as aviation and shipping; "
                "3. Track EIA inventory and OPEC signals dynamically and refresh risk assessment promptly."
            )
        else:
            advice = (
                "1. Current risk is manageable; maintain normal business exposure; "
                "2. Continue monitoring macro factors, with focus on DXY and VIX; "
                "3. Keep routine risk-review cadence for energy-sector clients."
            )

        return executive, detailed, advice

    def _contains_cjk(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text or ""))

    def _ensure_english_summary(self, text: str, prediction: PredictionResult) -> str:
        cleaned = (text or "").strip()
        if cleaned and not self._contains_cjk(cleaned):
            return cleaned
        return self._build_english_summary_fallback(prediction)

    def _build_english_summary_fallback(self, prediction: PredictionResult) -> str:
        risk = prediction.risk_assessment
        final_point = prediction.prediction_path[-1]
        return (
            f"The model projects an {risk.trend_display} move over the next {prediction.forecast_horizon} days, "
            f"with Brent expected near ${final_point.predicted_price:.2f}. "
            f"Estimated maximum return swing is {risk.max_return_change * 100:.2f}%, "
            f"risk level is {risk.level_display}, and confidence is {risk.confidence_score:.0%}."
        )

    def _ensure_english_detailed(
        self,
        text: str,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        explainability: ExplainabilitySection,
    ) -> str:
        cleaned = (text or "").strip()
        if cleaned and not self._contains_cjk(cleaned):
            return cleaned
        return self._build_english_detailed_fallback(prediction, industry_impact, explainability)

    def _ensure_english_advice(self, text: str, prediction: PredictionResult) -> str:
        cleaned = (text or "").strip()
        if cleaned and not self._contains_cjk(cleaned):
            return cleaned
        if prediction.risk_assessment.level in (RiskLevel.HIGH, RiskLevel.EXTREME):
            return (
                "1. Strengthen hedge coverage for oil-linked exposures and set explicit trigger bands; "
                "2. Tighten credit and liquidity monitoring for highly sensitive industries; "
                "3. Refresh scenario stress tests weekly with inventory and policy signals."
            )
        return (
            "1. Keep baseline exposure and financing rhythm stable under current risk conditions; "
            "2. Continue monitoring DXY, volatility indicators, and inventory surprises; "
            "3. Maintain a routine risk-review cadence and update controls when confidence changes materially."
        )

    def _build_english_detailed_fallback(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
        explainability: ExplainabilitySection,
    ) -> str:
        top_factors = [item.factor_name for item in explainability.top_factors[:3] if item.factor_name]
        factor_str = ", ".join(top_factors) if top_factors else "short-term momentum"
        final_point = prediction.prediction_path[-1]
        sorted_impacts = sorted(industry_impact.impacts, key=lambda x: x.impact_magnitude, reverse=True)
        top_industries = [item.industry for item in sorted_impacts[:3] if item.industry]
        industry_str = ", ".join(top_industries) if top_industries else "no high-alert sectors"
        return (
            f"This forecast is primarily driven by {factor_str}. "
            f"Brent is expected to move from ${prediction.current_price:.2f} to ${final_point.predicted_price:.2f} "
            f"over {prediction.forecast_horizon} days under a {prediction.risk_assessment.trend_display} regime. "
            f"Estimated return swing is {prediction.risk_assessment.max_return_change * 100:.2f}% with confidence "
            f"{prediction.risk_assessment.confidence_score:.0%}. "
            f"Industries requiring close monitoring include {industry_str}."
        )
