"""
AI 洞察服务：调用大语言模型生成油价风险分析文字摘要
"""
from __future__ import annotations

import os
from typing import List, Optional

_OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
_LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
_LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")


def generate_insight(
    horizon: str,
    q10: float,
    q50: float,
    q90: float,
    risk_level: str,
    factor_reasons: List[str],
) -> Optional[str]:
    """
    调用 LLM 根据预测结果和驱动因素生成简短的中文洞察文本。

    若未配置 OPENAI_API_KEY，则返回基于规则的降级摘要。

    Parameters
    ----------
    horizon:
        预测时间窗口，如 ``"7D"``。
    q10, q50, q90:
        分位数预测回报率。
    risk_level:
        风险等级字符串。
    factor_reasons:
        主要驱动因素说明列表。

    Returns
    -------
    str 或 None（LLM 调用失败时返回规则摘要）。
    """
    if not _OPENAI_API_KEY:
        return _fallback_insight(horizon, q50, risk_level, factor_reasons)

    try:
        import openai  # type: ignore

        client = openai.OpenAI(api_key=_OPENAI_API_KEY, base_url=_LLM_BASE_URL)
        factors_text = "\n".join(f"- {r}" for r in factor_reasons) or "（无可用因素数据）"
        prompt = (
            f"你是一位专业的大宗商品风险分析师。\n"
            f"以下是 {horizon} 时间窗口内的布伦特原油价格预测结果：\n"
            f"- 10% 分位数回报率: {q10:.2%}\n"
            f"- 50% 分位数回报率（中位数）: {q50:.2%}\n"
            f"- 90% 分位数回报率: {q90:.2%}\n"
            f"- 综合风险等级: {risk_level}\n"
            f"主要驱动因素：\n{factors_text}\n\n"
            f"请用不超过150字的中文，对当前油价风险状况给出简洁、专业的洞察摘要。"
        )
        resp = client.chat.completions.create(
            model=_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.3,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return _fallback_insight(horizon, q50, risk_level, factor_reasons)


def _fallback_insight(
    horizon: str,
    q50: float,
    risk_level: str,
    factor_reasons: List[str],
) -> str:
    """当 LLM 不可用时，生成基于规则的简单摘要。"""
    direction = "上涨" if q50 > 0 else "下跌" if q50 < 0 else "持平"
    top_factor = factor_reasons[0] if factor_reasons else "无显著驱动因素"
    return (
        f"未来 {horizon} 内，油价中位数预测为 {q50:.2%}，呈 {direction} 态势，"
        f"风险等级为 {risk_level}。{top_factor}"
    )
