"""
行业冲击映射服务

职责：
    - 基于知识图谱数据，将油价预测变化映射到各行业的冲击信号
    - 支持行业过滤
    - 输出 IndustryImpactResult

禁止：
    - 在此文件中调用模型
    - 在此文件中修改知识图谱数据
"""

import asyncio
from typing import Optional, Any
from openai import OpenAI, APIStatusError, AuthenticationError, RateLimitError
from app.schemas.model_response_schema import ModelRawResponse
from app.schemas.industry_schema import IndustryImpact, IndustryImpactResult
from app.core.constants import ImpactDirection, RiskLevel
from app.core.settings import settings
from app.utils.json_utils import safe_json_dumps, safe_json_loads
from app.core.logger import get_logger

logger = get_logger(__name__)


class IndustryService:
    """
    行业冲击映射服务。

    依赖知识图谱模块获取传导路径数据。
    """

    # 行业静态配置（可替换为从知识图谱动态加载）
    INDUSTRY_CONFIG: dict[str, dict] = {
        "aviation": {
            "name_cn": "航空业",
            "base_sensitivity": 0.85,
            "direction_policy": "negative",   # 油价涨 → 利空
            "key_indicators": ["航煤成本", "燃油附加费", "运营利润"],
            "transmission": ["原油→航煤→运营成本→净利润"],
        },
        "shipping": {
            "name_cn": "航运业",
            "base_sensitivity": 0.72,
            "direction_policy": "negative",
            "key_indicators": ["船用燃料成本", "运费率", "净利润"],
            "transmission": ["原油→重油→运营成本→运费"],
        },
        "chemical": {
            "name_cn": "化工业",
            "base_sensitivity": 0.78,
            "direction_policy": "negative",
            "key_indicators": ["乙烯裂解价差", "原料成本", "毛利率"],
            "transmission": ["原油→石脑油→乙烯→化工品价格"],
        },
        "energy": {
            "name_cn": "能源业",
            "base_sensitivity": 0.90,
            "direction_policy": "positive",   # 油价涨 → 利好
            "key_indicators": ["营业收入", "勘探利润", "储量价值"],
            "transmission": ["油价直接驱动收入"],
        },
        "manufacturing": {
            "name_cn": "制造业",
            "base_sensitivity": 0.45,
            "direction_policy": "negative",
            "key_indicators": ["能源成本占比", "生产成本", "出口竞争力"],
            "transmission": ["原油→电力→工业电价→成本"],
        },
        "agriculture": {
            "name_cn": "农业",
            "base_sensitivity": 0.50,
            "direction_policy": "negative",
            "key_indicators": ["化肥成本", "农机燃料", "农产品价格"],
            "transmission": ["原油→化肥原料→种植成本→粮价"],
        },
        "finance": {
            "name_cn": "金融业",
            "base_sensitivity": 0.30,
            "direction_policy": "neutral",
            "key_indicators": ["大宗商品贷款风险", "能源债券利差", "通胀预期"],
            "transmission": ["油价→通胀预期→利率预期→资产定价"],
        },
    }

    INDUSTRY_ALIAS_MAP: dict[str, str] = {
        "refinery": "chemical",
        "logistics": "shipping",
        "heavy_manufacturing": "manufacturing",
    }

    INDUSTRY_ALIAS_NAME_CN: dict[str, str] = {
        "refinery": "炼化业",
        "logistics": "物流业",
        "heavy_manufacturing": "高耗能制造业",
    }

    async def analyze_impact(
        self,
        model_response: ModelRawResponse,
        target_industries: Optional[list[str]] = None,
    ) -> IndustryImpactResult:
        """
        分析各行业受油价预测的冲击。

        Args:
            model_response: 云端模型原始响应。
            target_industries: 目标行业列表（None 表示全量分析）。

        Returns:
            IndustryImpactResult 行业冲击全量结果。
        """
        median = model_response.median
        industries_to_analyze = (
            target_industries
            if target_industries
            else list(self.INDUSTRY_CONFIG.keys())
        )

        impacts: list[IndustryImpact] = []
        high_alert: list[str] = []

        for industry_key in industries_to_analyze:
            base_key = self.INDUSTRY_ALIAS_MAP.get(industry_key, industry_key)
            config = self.INDUSTRY_CONFIG.get(base_key)
            if not config:
                logger.warning(f"未知行业标识符: {industry_key}，已跳过")
                continue

            industry_name_cn = self.INDUSTRY_ALIAS_NAME_CN.get(
                industry_key,
                config["name_cn"],
            )

            # 冲击强度 = |收益率变化| × 行业敏感度
            magnitude = min(abs(median) * config["base_sensitivity"] * 10, 1.0)

            # 冲击方向
            direction_policy = config["direction_policy"]
            if direction_policy == "positive":
                direction = (
                    ImpactDirection.POSITIVE if median > 0 else ImpactDirection.NEGATIVE
                )
            elif direction_policy == "negative":
                direction = (
                    ImpactDirection.NEGATIVE if median > 0 else ImpactDirection.POSITIVE
                )
            else:
                direction = ImpactDirection.NEUTRAL

            # 叙述文本
            dir_cn = {"positive": "利好", "negative": "利空", "neutral": "中性"}[
                direction_policy
            ]
            move_cn = "上涨" if median > 0 else "下跌"
            narrative = (
                f"预测油价{move_cn} {abs(median)*100:.2f}%，"
                f"对{config['name_cn']}形成{dir_cn}冲击，"
                f"影响强度 {magnitude:.0%}。"
                f"传导路径：{config['transmission'][0]}"
            )

            impact = IndustryImpact(
                industry=industry_key,
                industry_name_cn=industry_name_cn,
                impact_direction=direction,
                impact_magnitude=round(magnitude, 3),
                transmission_path=config["transmission"],
                key_indicators=config["key_indicators"],
                narrative=narrative,
            )
            impacts.append(impact)

            # 高预警判断
            if magnitude >= 0.5 and direction != ImpactDirection.NEUTRAL:
                high_alert.append(industry_key)

        llm_impacts: list[IndustryImpact] = []
        if settings.INDUSTRY_LLM_ENABLED:
            llm_impacts = await self._llm_refine_impacts(
                median=median,
                rule_impacts=impacts,
            )
        if llm_impacts:
            impacts = llm_impacts
            high_alert = [
                item.industry
                for item in impacts
                if item.impact_magnitude >= 0.5 and item.impact_direction != ImpactDirection.NEUTRAL
            ]

        logger.info(
            f"行业冲击分析完成 industries={len(impacts)} "
            f"high_alert={len(high_alert)} llm={'on' if llm_impacts else 'off'}"
        )

        return IndustryImpactResult(
            predicted_return_median=round(median, 6),
            impacts=impacts,
            high_alert_industries=high_alert,
        )

    async def _llm_refine_impacts(
        self,
        median: float,
        rule_impacts: list[IndustryImpact],
    ) -> list[IndustryImpact]:
        """
        使用 LLM 生成行业冲击饼图所需结构（严格 JSON），失败时回退规则结果。
        """
        if not settings.LLM_API_KEY.strip():
            return []

        payload = {
            "predicted_return_median": round(median, 6),
            "industries": [
                {
                    "industry": item.industry,
                    "industry_name_cn": item.industry_name_cn,
                    "rule_direction": item.impact_direction.value,
                    "rule_magnitude": item.impact_magnitude,
                    "transmission_path": item.transmission_path,
                    "key_indicators": item.key_indicators,
                }
                for item in rule_impacts
            ],
        }

        messages = [
            {
                "role": "system",
                "content": (
                    "你是企业银行风险分析助手。"
                    "请将输入行业冲击结果重排为可直接驱动饼图的数据。"
                    "只能使用输入中的行业与数值语义，不得虚构行业。"
                    "输出必须是 JSON 对象，且仅包含一个键 impacts。"
                    "impacts 是数组，每项包含字段：industry,direction,magnitude,narrative。"
                    "direction 仅允许 positive|negative|neutral。"
                    "magnitude 必须在 0~1，保留 3 位小数。"
                    "narrative 用中文一句话，描述油价变化对该行业的潜在影响。"
                ),
            },
            {
                "role": "user",
                "content": safe_json_dumps(payload),
            },
        ]

        try:
            raw = await self._call_llm(messages)
            parsed = safe_json_loads(raw)
            items = parsed.get("impacts") if isinstance(parsed, dict) else None
            if not isinstance(items, list):
                return []

            by_industry = {item.industry: item for item in rule_impacts}
            merged: list[IndustryImpact] = []
            for item in items:
                if not isinstance(item, dict):
                    continue

                industry = str(item.get("industry", "")).strip()
                if industry not in by_industry:
                    continue

                direction_str = str(item.get("direction", "neutral")).lower()
                if direction_str not in {"positive", "negative", "neutral"}:
                    continue

                try:
                    magnitude = float(item.get("magnitude", 0.0))
                except Exception:
                    continue
                magnitude = max(0.0, min(1.0, round(magnitude, 3)))

                base = by_industry[industry]
                merged.append(
                    IndustryImpact(
                        industry=industry,
                        industry_name_cn=base.industry_name_cn,
                        impact_direction=ImpactDirection(direction_str),
                        impact_magnitude=magnitude,
                        transmission_path=base.transmission_path,
                        key_indicators=base.key_indicators,
                        narrative=str(item.get("narrative", base.narrative))[:240],
                    )
                )

            if merged:
                return merged
        except Exception as err:
            logger.warning(f"行业冲击 LLM 增强失败，回退规则输出: {err}")

        return []

    async def _call_llm(self, messages: list[dict[str, str]]) -> str:
        client = OpenAI(api_key=settings.LLM_API_KEY, base_url=settings.LLM_BASE_URL)
        model_id = settings.LLM_MODEL_ID

        def _invoke() -> Any:
            return client.chat.completions.create(
                model=model_id,
                messages=messages,
                temperature=0.1,
                max_tokens=700,
                top_p=settings.LLM_TOP_P,
                frequency_penalty=settings.LLM_FREQUENCY_PENALTY,
                timeout=settings.LLM_TIMEOUT,
            )

        try:
            resp = await asyncio.to_thread(_invoke)
            content = (resp.choices[0].message.content or "").strip()
            if not content:
                raise RuntimeError("LLM 返回内容为空")
            if "```" in content:
                start = content.find("{")
                end = content.rfind("}")
                if start >= 0 and end > start:
                    content = content[start:end + 1]
            return content
        except (AuthenticationError, RateLimitError, APIStatusError) as err:
            raise RuntimeError(f"LLM 调用失败: {err}") from err
