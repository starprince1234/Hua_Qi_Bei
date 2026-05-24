"""
AI 解释增强服务

职责：
    - 并发调用不同模型，生成风险/行业/知识图谱详情解释
    - 对 LLM 输出做 JSON 约束解析
    - 在失败时提供规则降级结果
"""

import asyncio
import re
from typing import Any

from openai import OpenAI

from app.core.logger import get_logger
from app.core.settings import settings
from app.schemas.industry_schema import IndustryImpactResult
from app.schemas.prediction_schema import PredictionResult
from app.schemas.report_schema import (
    AIRiskInsight,
    AIIndustryInsight,
    AIKnowledgeGraphInsight,
    AIFinancingInsight,
)
from app.utils.json_utils import safe_json_dumps, safe_json_loads

logger = get_logger(__name__)


class AIInsightService:
    """分模块 AI 详情生成。"""

    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
            timeout=settings.LLM_TIMEOUT,
        )

    async def build_risk_insight(self, prediction: PredictionResult) -> AIRiskInsight:
        fallback = self._fallback_risk_insight(prediction)
        if not settings.LLM_API_KEY.strip():
            return fallback

        payload = {
            "horizon": prediction.forecast_horizon,
            "current_price": prediction.current_price,
            "final_price": prediction.prediction_path[-1].predicted_price,
            "max_return_change": prediction.risk_assessment.max_return_change,
            "confidence_score": prediction.risk_assessment.confidence_score,
            "trend": prediction.risk_assessment.trend_display,
        }
        messages = [
            {
                "role": "system",
                "content": (
                    settings.LLM_SYSTEM_PROMPT_RISK_DETAIL
                    + " Output strict JSON only: {\"risk_level\":\"LOW|MEDIUM|HIGH\",\"detail\":\"...\"}."
                ),
            },
            {"role": "user", "content": safe_json_dumps(payload)},
        ]
        try:
            raw = await self._call_llm(settings.LLM_MODEL_RISK_LEVEL, messages)
            parsed = safe_json_loads(raw)
            level = str(parsed.get("risk_level", "")).upper()
            if level not in {"LOW", "MEDIUM", "HIGH"}:
                level = fallback.risk_level
            detail = str(parsed.get("detail", "")).strip() or fallback.detail
            return AIRiskInsight(
                risk_level=level,
                detail=detail[:1200],
                model_id=settings.LLM_MODEL_RISK_LEVEL,
            )
        except Exception as err:
            logger.warning(f"风险详情 LLM 失败，回退规则输出: {err}")
            return fallback

    async def build_industry_insight(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
    ) -> AIIndustryInsight:
        fallback = self._fallback_industry_insight(prediction, industry_impact)
        if not settings.LLM_API_KEY.strip():
            return fallback

        payload = {
            "predicted_return": prediction.prediction_path[-1].predicted_return,
            "industries": [
                {
                    "industry": item.industry,
                    "magnitude": item.impact_magnitude,
                    "direction": item.impact_direction.value,
                    "narrative": item.narrative,
                }
                for item in industry_impact.impacts
            ],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    settings.LLM_SYSTEM_PROMPT_INDUSTRY_DETAIL
                    + " Output strict JSON only: {\"detail\":\"...\"}. "
                    + "The detail must explain percentage derivation and calculation logic."
                ),
            },
            {"role": "user", "content": safe_json_dumps(payload)},
        ]

        try:
            raw = await self._call_llm(settings.LLM_MODEL_INDUSTRY_IMPACT, messages)
            parsed = safe_json_loads(raw)
            detail = str(parsed.get("detail", "")).strip() or fallback.detail
            return AIIndustryInsight(detail=detail[:2000], model_id=settings.LLM_MODEL_INDUSTRY_IMPACT)
        except Exception as err:
            logger.warning(f"行业详情 LLM 失败，回退规则输出: {err}")
            return fallback

    async def build_kg_insight(
        self,
        prediction: PredictionResult,
        knowledge_graph_paths: list[dict[str, Any]],
    ) -> tuple[AIKnowledgeGraphInsight, dict[str, dict[str, str]]]:
        fallback_insight, fallback_levels = self._fallback_kg_insight(knowledge_graph_paths)
        if not settings.LLM_API_KEY.strip() or not knowledge_graph_paths:
            return fallback_insight, fallback_levels

        payload = {
            "predicted_return": prediction.prediction_path[-1].predicted_return,
            "paths": knowledge_graph_paths,
            "allowed_levels": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "MINOR", "NONE"],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    settings.LLM_SYSTEM_PROMPT_KG_DETAIL
                    + " Output strict JSON only: {\"detail\":\"...\",\"node_levels\":[{\"industry\":\"...\",\"nodes\":[{\"name\":\"...\",\"level\":\"...\"}]}]}."
                    + " The detail must cover every industry and every node, including direction, strength rationale, downstream transmission, and cross-industry comparison."
                    + " Target at least 450 words."
                ),
            },
            {"role": "user", "content": safe_json_dumps(payload)},
        ]

        try:
            raw = await self._call_llm(settings.LLM_MODEL_KNOWLEDGE_GRAPH, messages)
            parsed = safe_json_loads(raw)
            detail = str(parsed.get("detail", "")).strip()

            node_levels_map: dict[str, dict[str, str]] = {}
            items = parsed.get("node_levels")
            if isinstance(items, list):
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    industry = str(item.get("industry", "")).strip()
                    nodes = item.get("nodes", [])
                    if not industry or not isinstance(nodes, list):
                        continue
                    node_levels_map[industry] = {}
                    for node in nodes:
                        if not isinstance(node, dict):
                            continue
                        name = str(node.get("name", "")).strip()
                        level = str(node.get("level", "")).strip()
                        if name and level:
                            node_levels_map[industry][name] = level

            if not node_levels_map:
                node_levels_map = fallback_levels

            if len(detail) < 220:
                detail = self._build_detailed_kg_detail(
                    knowledge_graph_paths=knowledge_graph_paths,
                    node_levels_map=node_levels_map,
                    predicted_return=prediction.prediction_path[-1].predicted_return,
                )

            if not detail:
                detail = fallback_insight.detail

            return (
                AIKnowledgeGraphInsight(
                    detail=detail[:2500],
                    model_id=settings.LLM_MODEL_KNOWLEDGE_GRAPH,
                ),
                node_levels_map,
            )
        except Exception as err:
            logger.warning(f"知识图谱详情 LLM 失败，回退规则输出: {err}")
            return fallback_insight, fallback_levels

    async def build_financing_insight(
        self,
        prediction: PredictionResult,
        industries: list[str],
        top_factors: list[dict[str, Any]],
    ) -> AIFinancingInsight:
        fallback = self._fallback_financing_insight(prediction, industries, top_factors)
        if not settings.LLM_API_KEY.strip():
            return fallback

        payload = {
            "benchmark": "Brent crude",
            "current_price": prediction.current_price,
            "horizon_days": prediction.forecast_horizon,
            "trend": prediction.risk_assessment.trend_display,
            "risk_level": prediction.risk_assessment.level_display,
            "confidence_score": prediction.risk_assessment.confidence_score,
            "predicted_return": prediction.prediction_path[-1].predicted_return,
            "price_lower": prediction.prediction_path[-1].lower_price,
            "price_upper": prediction.prediction_path[-1].upper_price,
            "selected_entities": industries,
            "top_factors": top_factors,
            "required_output": {
                "module_1": "oil price trend and driver logic review",
                "module_2": "entity-level recommendations including financing/procurement/inventory/hedging",
                "module_3": "implementation safeguards and differentiation advantages",
                "language": "English",
            },
        }

        messages = [
            {
                "role": "system",
                "content": (
                    settings.LLM_SYSTEM_PROMPT_FINANCING_RECOMMENDATION
                    + " Output strict JSON only: {\"detail\":\"...\"}. "
                    + "Output plain text only (no Markdown headings, no bullet markers like #, *, -, or numbered list prefixes)."
                ),
            },
            {"role": "user", "content": safe_json_dumps(payload)},
        ]

        try:
            raw = await self._call_llm(
                settings.LLM_MODEL_FINANCING_RECOMMENDATION,
                messages,
                max_tokens_override=max(4000, settings.LLM_MAX_TOKENS + 2500),
            )
            parsed = safe_json_loads(raw)
            detail = str(parsed.get("detail", "")).strip() or fallback.detail
            detail = self._normalize_plain_text(detail)
            return AIFinancingInsight(
                detail=detail,
                model_id=settings.LLM_MODEL_FINANCING_RECOMMENDATION,
            )
        except Exception as err:
            logger.warning(f"融资建议 LLM 失败，回退规则输出: {err}")
            return fallback

    async def _call_llm(
        self,
        model_id: str,
        messages: list[dict[str, str]],
        max_tokens_override: int | None = None,
    ) -> str:
        def _invoke() -> Any:
            return self._client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.2,
                top_p=settings.LLM_TOP_P,
                frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
                max_tokens=max_tokens_override or min(1800, settings.LLM_MAX_TOKENS + 300),
                stream=False,
                extra_body={"response_format": {"type": "json_object"}},
            )

        resp = await asyncio.to_thread(_invoke)
        content = (resp.choices[0].message.content or "").strip()
        if not content:
            raise RuntimeError("LLM 返回空内容")
        if "```" in content:
            start = content.find("{")
            end = content.rfind("}")
            if start >= 0 and end > start:
                content = content[start:end + 1]
        return content

    def _fallback_risk_insight(self, prediction: PredictionResult) -> AIRiskInsight:
        level = prediction.risk_assessment.level.value.upper()
        if level == "EXTREME":
            level = "HIGH"
        trend = str(prediction.risk_assessment.trend_display or "sideways")
        detail = (
            f"Based on the {prediction.forecast_horizon}-day forecast, the oil-price trend is {trend}, "
            f"with a maximum return swing of about {prediction.risk_assessment.max_return_change * 100:.2f}%, "
            f"and model confidence around {prediction.risk_assessment.confidence_score * 100:.1f}%. "
            f"Therefore, the assessed risk level is {level}."
        )
        return AIRiskInsight(
            risk_level=level,
            detail=detail,
            model_id=settings.LLM_MODEL_RISK_LEVEL,
        )

    def _fallback_industry_insight(
        self,
        prediction: PredictionResult,
        industry_impact: IndustryImpactResult,
    ) -> AIIndustryInsight:
        lines: list[str] = []
        for item in industry_impact.impacts:
            lines.append(
                f"{item.industry}: based on forecast return {prediction.prediction_path[-1].predicted_return * 100:.2f}% "
                f"and industry sensitivity mapping, the estimated shock magnitude is {item.impact_magnitude * 100:.1f}% "
                f"(direction: {item.impact_direction.value})."
            )
        detail = "\n".join(lines) if lines else "No industry shock explanation is currently available."
        return AIIndustryInsight(detail=detail[:2000], model_id=settings.LLM_MODEL_INDUSTRY_IMPACT)

    def _fallback_kg_insight(
        self,
        knowledge_graph_paths: list[dict[str, Any]],
    ) -> tuple[AIKnowledgeGraphInsight, dict[str, dict[str, str]]]:
        default_levels = ["HIGH", "MEDIUM", "LOW", "MINOR"]
        node_levels_map: dict[str, dict[str, str]] = {}

        for path in knowledge_graph_paths:
            industry = str(path.get("industry", "")).strip()
            labels = path.get("path_labels") or []
            if not industry or not isinstance(labels, list):
                continue
            node_levels_map[industry] = {}
            for idx, name in enumerate(labels):
                level = default_levels[min(idx, len(default_levels) - 1)]
                node_levels_map[industry][str(name)] = level

        detail = self._build_detailed_kg_detail(
            knowledge_graph_paths=knowledge_graph_paths,
            node_levels_map=node_levels_map,
            predicted_return=0.0,
        )
        return (
            AIKnowledgeGraphInsight(
                detail=detail,
                model_id=settings.LLM_MODEL_KNOWLEDGE_GRAPH,
            ),
            node_levels_map,
        )

    def _build_detailed_kg_detail(
        self,
        knowledge_graph_paths: list[dict[str, Any]],
        node_levels_map: dict[str, dict[str, str]],
        predicted_return: float,
    ) -> str:
        if not knowledge_graph_paths:
            return "No knowledge-graph paths are available for detailed analysis."

        direction_text = "upward" if predicted_return >= 0 else "downward"
        lines: list[str] = [
            f"This forecast indicates an expected {direction_text} oil-price move (return about {predicted_return * 100:.2f}%). "
            "Transmission analysis by industry is as follows:"
        ]

        for path in knowledge_graph_paths:
            industry = str(path.get("industry", "")).strip() or "unknown_industry"
            labels = path.get("path_labels") or []
            if not isinstance(labels, list) or not labels:
                continue
            level_map = node_levels_map.get(industry, {})

            lines.append(f"[{industry}] transmission path: {' -> '.join(str(x) for x in labels)}")
            for idx, node_name in enumerate(labels):
                node = str(node_name)
                level = level_map.get(node, "MEDIUM")
                if idx == 0:
                    stage = "upstream trigger"
                    propagation = "Changes at this node directly affect cost or supply-demand expectations and act as the first shock source in the chain."
                elif idx == len(labels) - 1:
                    stage = "downstream outcome"
                    propagation = "This node captures terminal pressure or benefit, reflecting final profitability and valuation elasticity."
                else:
                    stage = "intermediate transmission"
                    propagation = "This node amplifies or dampens the shock and passes the impact to the next stage."

                lines.append(
                    f"- Node {idx + 1}: {node} ({stage}, impact level: {level}). "
                    f"Under a {direction_text} oil-price scenario, {propagation}"
                )

            lines.append(
                f"{industry} summary: if upstream nodes show higher impact levels, the middle and downstream stages often face "
                "margin pressure or inventory-stress redistribution. Continuous tracking of cash flow, hedge coverage, "
                "and cost pass-through capacity is recommended."
            )

        lines.append(
            "Cross-industry note: prioritize sectors with shorter paths, higher node impact levels, and weaker terminal demand elasticity, "
            "as they are usually more sensitive to oil-price shocks."
        )
        return "\n".join(lines)[:2500]

    def _fallback_financing_insight(
        self,
        prediction: PredictionResult,
        industries: list[str],
        top_factors: list[dict[str, Any]],
    ) -> AIFinancingInsight:
        factor_lines = []
        for item in top_factors[:5]:
            name = str(item.get("factor") or item.get("factor_name") or "Unknown factor")
            val = float(item.get("contribution") or item.get("shap_value") or 0.0)
            factor_lines.append(f"- {name}: contribution={val:.6f}")

        entity_lines = []
        for entity in industries:
            entity_lines.append(
                f"{entity}\n"
                "Financing Advice: Prioritize staged drawdown and combine working-capital lines with hedging-linked facilities.\n"
                "Procurement Rhythm: Use tranche purchases with trigger prices and dynamic long-term vs spot allocation.\n"
                "Inventory Management: Tighten safety-stock bands and monitor mark-to-market exposure weekly.\n"
                "Hedging Arrangement: Apply layered hedging (futures/options/swaps) with risk-limit governance."
            )

        detail = (
            "Module 1 - Oil Price Trend and Driver Logic Review\n"
            f"Benchmark: Brent crude\n"
            f"Forecast horizon: {prediction.forecast_horizon} days\n"
            f"Predicted trend: {prediction.risk_assessment.trend_display}\n"
            f"Expected return: {prediction.prediction_path[-1].predicted_return * 100:.2f}%\n"
            f"Price range: {prediction.prediction_path[-1].lower_price:.2f} to {prediction.prediction_path[-1].upper_price:.2f}\n"
            "Assumption: In the absence of additional corporate constraints, recommendations are built on generic treasury and risk-policy practices.\n\n"
            "Key Driver Snapshot\n"
            + ("\n".join(factor_lines) if factor_lines else "No factor details available from current request.\n")
            + "\n\nModule 2 - Entity-Level Decision Conversion Recommendations\n"
            + ("\n\n".join(entity_lines) if entity_lines else "No target entities were selected.\n")
            + "\n\nModule 3 - Implementation Safeguards and Differentiation Advantages\n"
            "Build a weekly monitoring loop that refreshes forecast, confidence score, and driver ranking.\n"
            "Link financing terms and hedge ratio to model-updated risk bands for dynamic optimization.\n"
            "Different from pure price-forecast tools: this framework closes the loop from signal to financing action, with explainability and control checkpoints."
        )

        return AIFinancingInsight(
            detail=self._normalize_plain_text(detail)[:6000],
            model_id=settings.LLM_MODEL_FINANCING_RECOMMENDATION,
        )

    def _normalize_plain_text(self, text: str) -> str:
        content = text.replace("\r\n", "\n")
        content = re.sub(r"^\s{0,3}#{1,6}\s*", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*[-*+]\s+", "", content, flags=re.MULTILINE)
        content = re.sub(r"^\s*\d+[\.)]\s+", "", content, flags=re.MULTILINE)
        content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
        content = re.sub(r"__(.*?)__", r"\1", content)
        content = re.sub(r"`([^`]*)`", r"\1", content)
        content = re.sub(r"\n{3,}", "\n\n", content)
        return content.strip()
