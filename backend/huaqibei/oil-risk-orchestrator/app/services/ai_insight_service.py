from __future__ import annotations

from app.core.logger import get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

_RISK_LEVEL_ZH = {
    "low": "低",
    "medium": "中等",
    "high": "高",
    "extreme": "极高",
}


async def generate_insight(
    predictions: list[float],
    risk_metrics: dict,
    factor_contributions: list,
    horizon: int,
    language: str = "zh",
) -> str:
    """
    Generate an AI-flavoured insight string.
    Tries the configured LLM endpoint first; falls back to a deterministic template.
    """
    settings = get_settings()
    if settings.LLM_API_KEY:
        try:
            return await _llm_insight(predictions, risk_metrics, factor_contributions, horizon, settings)
        except Exception as exc:
            logger.warning("LLM insight failed, using template", extra={"error": str(exc)})

    return _template_insight(predictions, risk_metrics, factor_contributions, horizon)


async def _llm_insight(predictions, risk_metrics, factor_contributions, horizon, settings) -> str:
    from app.utils.http_client import get_async_client

    top_factors = [fc.label for fc in factor_contributions[:3] if hasattr(fc, "label")]
    factors_str = "、".join(top_factors) if top_factors else "多种宏观因素"
    risk_level_zh = _RISK_LEVEL_ZH.get(risk_metrics.get("risk_level", "medium"), "中等")
    prompt = (
        f"以下是油价预测结果摘要：预测期{horizon}天，风险等级{risk_level_zh}，"
        f"主要驱动因素包括{factors_str}。请用不超过150字的中文专业语言撰写油价风险分析摘要。"
    )
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }
    async with get_async_client() as client:
        resp = await client.post(
            settings.LLM_API_URL,
            json=payload,
            headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        )
        resp.raise_for_status()
        data = resp.json()
    return data["choices"][0]["message"]["content"].strip()


def _template_insight(predictions, risk_metrics, factor_contributions, horizon: int) -> str:
    risk_level = risk_metrics.get("risk_level", "medium")
    risk_level_zh = _RISK_LEVEL_ZH.get(risk_level, "中等")
    start_price = predictions[0] if predictions else 0.0
    end_price = predictions[-1] if predictions else 0.0
    change = end_price - start_price
    direction = "上行" if change >= 0 else "下行"

    top_factors = [fc.label for fc in factor_contributions[:3] if hasattr(fc, "label")]
    factors_str = "、".join(top_factors) if top_factors else "宏观供需基本面"

    volatility = risk_metrics.get("volatility", 0.0)
    var_95 = risk_metrics.get("var_95", 0.0)

    return (
        f"综合模型预测，未来{horizon}天国际原油价格整体呈{direction}趋势，"
        f"预计变动幅度约{abs(change):.2f}美元/桶，风险等级为{risk_level_zh}。"
        f"当前波动率估计为{volatility:.2%}，95%置信区间在险价值（VaR）为{var_95:.2f}美元/桶。"
        f"主要驱动因素包括{factors_str}，建议密切关注相关指标变化，合理配置能源对冲头寸。"
    )
