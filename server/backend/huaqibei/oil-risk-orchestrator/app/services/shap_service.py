"""
SHAP 解释服务

职责：
    - 解析模型返回的 SHAP 值
    - 在模型未返回 SHAP 时构建代理解释
    - 输出标准化因子贡献列表

禁止：
    - 在此文件中做推理计算
    - 在此文件中调用模型 API
"""

from typing import Optional
from app.schemas.model_response_schema import ModelRawResponse
from app.schemas.report_schema import FactorContribution, ExplainabilitySection
from app.core.logger import get_logger

logger = get_logger(__name__)

# 因子中文名映射字典（可扩展）
FACTOR_NAME_MAP: dict[str, str] = {
    "return_lag_1": "1日滞后收益率",
    "return_lag_3": "3日滞后收益率",
    "return_lag_5": "5日滞后收益率",
    "return_lag_10": "10日滞后收益率",
    "return_lag_20": "20日滞后收益率",
    "rolling_mean_5": "5日滚动均值",
    "rolling_mean_10": "10日滚动均值",
    "rolling_mean_20": "20日滚动均值",
    "rolling_std_5": "5日滚动波动率",
    "rolling_std_10": "10日滚动波动率",
    "rolling_std_20": "20日滚动波动率",
    "macro_dxy": "美元指数(DXY)",
    "macro_vix": "VIX恐慌指数",
    "macro_sp500": "标普500指数",
    "macro_us_10y_yield": "美10年期国债收益率",
    "macro_eia_inventory": "EIA原油库存变化",
    "macro_opec_output": "OPEC产量",
    "interact_return_dxy": "收益率×美元交互项",
    "interact_return_vix": "收益率×VIX交互项",
    "interact_sharpe_5": "5日夏普调整因子",
    "interact_eia_momentum": "EIA供需动量",
}


class ShapService:
    """
    SHAP 解释服务。

    情况 A：模型直接返回 SHAP 值 → 直接解析 top-N 因子
    情况 B：模型未返回 SHAP → 构建代理贡献文本（基于特征命名规则）
    """

    def build_explainability(
        self,
        model_response: ModelRawResponse,
        top_n: int = 8,
    ) -> ExplainabilitySection:
        """
        构建可解释性分析章节。

        Args:
            model_response: 云端模型原始响应。
            top_n: 展示 Top N 个贡献因子。

        Returns:
            ExplainabilitySection 可解释性分析结果。
        """
        if model_response.shap_values and model_response.shap_values.values:
            logger.info("使用模型返回的 SHAP 值进行解释")
            top_factors = self._parse_shap_values(
                model_response.shap_values.values,
                model_response.shap_values.base_value,
                top_n,
            )
        else:
            logger.warning("模型未返回 SHAP 值，使用代理解释模式")
            top_factors = self._build_proxy_contributions(model_response, top_n)

        summary = self._build_summary(top_factors, model_response.median)

        return ExplainabilitySection(
            top_factors=top_factors,
            knowledge_graph_narrative="",   # 由知识图谱模块填充
            summary=summary,
        )

    def _parse_shap_values(
        self,
        shap_values: dict[str, float],
        base_value: float,
        top_n: int,
    ) -> list[FactorContribution]:
        """
        解析 SHAP 值字典，返回按绝对值降序的 Top N 因子。

        Args:
            shap_values: 特征名 → SHAP 值字典。
            base_value: SHAP 基准值。
            top_n: 保留前 N 个。

        Returns:
            FactorContribution 列表。
        """
        sorted_factors = sorted(
            shap_values.items(), key=lambda x: abs(x[1]), reverse=True
        )[:top_n]

        contributions = []
        for factor_name, shap_val in sorted_factors:
            factor_cn = FACTOR_NAME_MAP.get(factor_name, factor_name)
            direction = "正向驱动" if shap_val > 0 else "负向抑制"
            description = (
                f"{factor_cn}对油价{'' if shap_val > 0 else '下'}行贡献 "
                f"SHAP={shap_val:+.4f}"
            )
            contributions.append(
                FactorContribution(
                    factor_name=factor_name,
                    factor_name_cn=factor_cn,
                    shap_value=round(shap_val, 6),
                    direction=direction,
                    description=description,
                )
            )

        return contributions

    def _build_proxy_contributions(
        self,
        model_response: ModelRawResponse,
        top_n: int,
    ) -> list[FactorContribution]:
        """
        模型未返回 SHAP 时，构建代理因子贡献（基于宏观知识）。

        Args:
            model_response: 模型响应（从中读取 median 方向）。
            top_n: 保留前 N 个。

        Returns:
            FactorContribution 列表（代理模式）。
        """
        median = model_response.median
        sign = 1 if median > 0 else -1

        proxy_factors = [
            ("return_lag_1", sign * 0.035, "短期动量延续"),
            ("macro_dxy", -sign * 0.028, "美元汇率反向压制"),
            ("macro_eia_inventory", sign * 0.022, "库存变化驱动"),
            ("rolling_std_5", sign * 0.018, "近期波动率放大"),
            ("macro_vix", -sign * 0.015, "市场恐慌情绪"),
            ("interact_return_dxy", sign * 0.012, "汇率-收益率联动"),
            ("return_lag_5", sign * 0.010, "5日趋势延续"),
            ("macro_opec_output", sign * 0.008, "OPEC供给调控"),
        ]

        contributions = []
        for factor_name, proxy_shap, desc in proxy_factors[:top_n]:
            factor_cn = FACTOR_NAME_MAP.get(factor_name, factor_name)
            direction = "正向驱动" if proxy_shap > 0 else "负向抑制"
            contributions.append(
                FactorContribution(
                    factor_name=factor_name,
                    factor_name_cn=factor_cn,
                    shap_value=round(proxy_shap, 6),
                    direction=direction,
                    description=f"[代理模式] {desc}，贡献值={proxy_shap:+.4f}",
                )
            )

        return contributions

    def _build_summary(
        self,
        top_factors: list[FactorContribution],
        median: float,
    ) -> str:
        """
        构建解释层综合摘要。

        Args:
            top_factors: Top 因子列表。
            median: 预测收益率中位数。

        Returns:
            自然语言摘要字符串。
        """
        if not top_factors:
            return "暂无因子解释数据。"

        top3 = [f.factor_name_cn for f in top_factors[:3]]
        direction = "上行" if median > 0 else "下行"
        return (
            f"本次油价{direction}预测主要受以下因子驱动：{', '.join(top3)}。"
            f"其中{'、'.join(top3[:2])}对预测方向贡献最为显著。"
        )
