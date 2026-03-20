from __future__ import annotations

# Mapping: English factor name -> {label (Chinese), category (Chinese)}
FACTOR_DICT: dict[str, dict[str, str]] = {
    "geopolitical_risk": {"label": "地缘政治风险", "category": "政治因素"},
    "opec_production": {"label": "OPEC产量", "category": "供应因素"},
    "us_rig_count": {"label": "美国石油钻井数", "category": "供应因素"},
    "crude_inventory": {"label": "原油库存", "category": "供应因素"},
    "global_demand": {"label": "全球石油需求", "category": "需求因素"},
    "china_pmi": {"label": "中国制造业PMI", "category": "需求因素"},
    "us_gdp_growth": {"label": "美国GDP增速", "category": "需求因素"},
    "usd_index": {"label": "美元指数", "category": "金融因素"},
    "sp500": {"label": "标普500指数", "category": "金融因素"},
    "vix": {"label": "VIX波动率指数", "category": "金融因素"},
    "10y_treasury_yield": {"label": "美国10年期国债收益率", "category": "金融因素"},
    "brent_wti_spread": {"label": "布伦特-WTI价差", "category": "价格因素"},
    "natural_gas_price": {"label": "天然气价格", "category": "能源替代"},
    "refinery_utilization": {"label": "炼油厂开工率", "category": "供应因素"},
    "shipping_freight": {"label": "波罗的海干散货指数", "category": "需求因素"},
    "aviation_fuel_demand": {"label": "航空燃油需求", "category": "需求因素"},
    "renewable_capacity": {"label": "可再生能源装机量", "category": "能源替代"},
    "sanctions_index": {"label": "制裁压力指数", "category": "政治因素"},
    "weather_index": {"label": "极端天气指数", "category": "环境因素"},
    "speculative_position": {"label": "投机净头寸", "category": "金融因素"},
}
