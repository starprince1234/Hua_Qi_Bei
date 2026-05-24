"""
因子解释字典

职责：
    - 维护因子的中英文映射、分类标签、定义文本
    - 供 SHAP 解释和报告生成使用

禁止：
    - 在此文件中写业务逻辑
"""

from app.core.constants import FactorCategory


# 因子元数据字典
FACTOR_METADATA: dict[str, dict] = {
    "return_lag_1": {
        "name_cn": "1日滞后收益率",
        "category": FactorCategory.TECHNICAL,
        "definition": "前1日原油对数收益率，捕捉短期动量效应",
        "unit": "无量纲",
    },
    "return_lag_3": {
        "name_cn": "3日滞后收益率",
        "category": FactorCategory.TECHNICAL,
        "definition": "前3日原油对数收益率",
        "unit": "无量纲",
    },
    "return_lag_5": {
        "name_cn": "5日滞后收益率",
        "category": FactorCategory.TECHNICAL,
        "definition": "前5日原油对数收益率，捕捉中期动量",
        "unit": "无量纲",
    },
    "return_lag_10": {
        "name_cn": "10日滞后收益率",
        "category": FactorCategory.TECHNICAL,
        "definition": "前10日原油对数收益率",
        "unit": "无量纲",
    },
    "return_lag_20": {
        "name_cn": "20日滞后收益率",
        "category": FactorCategory.TECHNICAL,
        "definition": "前20日原油对数收益率，捕捉月线动量",
        "unit": "无量纲",
    },
    "rolling_mean_5": {
        "name_cn": "5日均价",
        "category": FactorCategory.TECHNICAL,
        "definition": "近5个交易日收盘价移动平均",
        "unit": "USD/桶",
    },
    "rolling_std_5": {
        "name_cn": "5日波动率",
        "category": FactorCategory.TECHNICAL,
        "definition": "近5个交易日收盘价标准差，度量短期价格波动",
        "unit": "USD/桶",
    },
    "macro_dxy": {
        "name_cn": "美元指数(DXY)",
        "category": FactorCategory.MACRO,
        "definition": "美元对一篮子货币的综合汇率指数。"
                      "美元走强通常压制以美元计价的油价",
        "unit": "指数点",
    },
    "macro_vix": {
        "name_cn": "VIX恐慌指数",
        "category": FactorCategory.FINANCIAL,
        "definition": "标普500期权隐含波动率，市场情绪风险温度计",
        "unit": "百分比",
    },
    "macro_eia_inventory": {
        "name_cn": "EIA原油库存变化",
        "category": FactorCategory.SUPPLY,
        "definition": "美国能源信息署周度原油库存变化量。"
                      "库存下降通常支撑油价",
        "unit": "万桶",
    },
    "macro_opec_output": {
        "name_cn": "OPEC产量",
        "category": FactorCategory.SUPPLY,
        "definition": "OPEC成员国月度总产量，直接影响供给端",
        "unit": "百万桶/天",
    },
    "interact_return_dxy": {
        "name_cn": "收益率×美元交互项",
        "category": FactorCategory.FINANCIAL,
        "definition": "捕捉油价动量与美元强弱的非线性联动关系",
        "unit": "无量纲",
    },
    "interact_return_vix": {
        "name_cn": "收益率×VIX交互项",
        "category": FactorCategory.FINANCIAL,
        "definition": "捕捉油价动量在高波动环境下的放大效应",
        "unit": "无量纲",
    },
}


def get_factor_info(factor_name: str) -> dict:
    """
    查询因子元数据。

    Args:
        factor_name: 因子标识符。

    Returns:
        因子元数据字典，若未找到则返回基础占位信息。
    """
    return FACTOR_METADATA.get(
        factor_name,
        {
            "name_cn": factor_name,
            "category": FactorCategory.TECHNICAL,
            "definition": "自定义因子",
            "unit": "未知",
        },
    )
