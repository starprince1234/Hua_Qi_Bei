"""
AI 解释增强服务

职责：
    - 并发调用不同模型，生成风险/行业/知识图谱详情解释
    - 对 LLM 输出做 JSON 约束解析
    - 在失败时提供规则降级结果
"""

import asyncio
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
                    + "输出严格 JSON：{\"risk_level\":\"LOW|MEDIUM|HIGH\",\"detail\":\"...\"}"
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
                    + "输出严格 JSON：{\"detail\":\"...\"}，detail 需解释百分比来源与计算逻辑。"
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
            "allowed_levels": ["最严重", "严重", "中", "较轻微", "轻微", "无"],
        }
        messages = [
            {
                "role": "system",
                "content": (
                    settings.LLM_SYSTEM_PROMPT_KG_DETAIL
                    + "输出严格 JSON：{\"detail\":\"...\",\"node_levels\":[{\"industry\":\"...\",\"nodes\":[{\"name\":\"...\",\"level\":\"...\"}]}]}。"
                    + "detail 必须覆盖每个行业和每个节点，至少包含节点影响方向、强度原因、向下游传导解释与行业间对比。"
                    + "detail 建议不少于 450 字。"
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

    async def _call_llm(self, model_id: str, messages: list[dict[str, str]]) -> str:
        def _invoke() -> Any:
            return self._client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.2,
                top_p=settings.LLM_TOP_P,
                frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
                max_tokens=min(1800, settings.LLM_MAX_TOKENS + 300),
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
        detail = (
            f"基于{prediction.forecast_horizon}天预测结果，油价趋势为{prediction.risk_assessment.trend_display}，"
            f"最大收益变动约{prediction.risk_assessment.max_return_change * 100:.2f}%，"
            f"模型置信度约{prediction.risk_assessment.confidence_score * 100:.1f}%，"
            f"因此评定风险等级为{level}。"
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
                f"{item.industry}：基于预测收益率{prediction.prediction_path[-1].predicted_return * 100:.2f}%"
                f"与行业敏感度映射，冲击强度为{item.impact_magnitude * 100:.1f}%（方向：{item.impact_direction.value}）。"
            )
        detail = "\n".join(lines) if lines else "暂无行业冲击可解释信息。"
        return AIIndustryInsight(detail=detail[:2000], model_id=settings.LLM_MODEL_INDUSTRY_IMPACT)

    def _fallback_kg_insight(
        self,
        knowledge_graph_paths: list[dict[str, Any]],
    ) -> tuple[AIKnowledgeGraphInsight, dict[str, dict[str, str]]]:
        default_levels = ["严重", "中", "较轻微", "轻微"]
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
            return "暂无可用于展开分析的知识图谱路径。"

        direction_text = "上行" if predicted_return >= 0 else "下行"
        lines: list[str] = [
            f"本轮预测显示油价预期{direction_text}（收益率约 {predicted_return * 100:.2f}%），传导分析按行业逐条展开如下："
        ]

        for path in knowledge_graph_paths:
            industry = str(path.get("industry", "")).strip() or "未知行业"
            labels = path.get("path_labels") or []
            if not isinstance(labels, list) or not labels:
                continue
            level_map = node_levels_map.get(industry, {})

            lines.append(f"【{industry}】传导路径：{' -> '.join(str(x) for x in labels)}")
            for idx, node_name in enumerate(labels):
                node = str(node_name)
                level = level_map.get(node, "中")
                if idx == 0:
                    stage = "上游起点"
                    propagation = "该节点变化会直接改变成本或供需预期，是全链路首个冲击源。"
                elif idx == len(labels) - 1:
                    stage = "末端承接"
                    propagation = "该节点主要体现终端承压或受益结果，反映最终盈利与估值弹性。"
                else:
                    stage = "中间传导"
                    propagation = "该节点承担冲击放大/衰减作用，并将影响继续传递至下一环节。"

                lines.append(
                    f"- 节点{idx + 1}：{node}（{stage}，影响等级：{level}）。"
                    f"在油价{direction_text}情景下，{propagation}"
                )

            lines.append(
                f"{industry}小结：若上游节点等级偏高，链路中后段通常会出现利润率或库存压力再分配，"
                f"建议结合该行业现金流、对冲覆盖率与成本传导能力持续跟踪。"
            )

        lines.append("横向对比建议：优先关注路径更短、节点等级更高且末端需求弹性更弱的行业，这类行业对油价冲击更敏感。")
        return "\n".join(lines)[:2500]
