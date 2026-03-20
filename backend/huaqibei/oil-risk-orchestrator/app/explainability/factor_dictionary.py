"""
因子字典

职责：
    - 维护特征名到中文可读名称的映射
    - 提供特征分组信息（宏观/价格/波动率/衍生）
"""

FACTOR_DISPLAY_NAMES: dict[str, str] = {
    "Brent_Crude(BZ=F)_Close": "布伦特原油收盘价",
    "WTI_Crude(CL=F)_Close": "WTI 原油收盘价",
    "OVX": "原油波动率指数(OVX)",
    "DXY": "美元指数(DXY)",
    "T5YIE": "5年期通胀预期(T5YIE)",
    "Gasoline": "汽油期货价格",
    "OVX_日涨跌幅 (%)": "OVX 日涨跌幅",
    "Brent_当日波动幅度(%)": "布伦特日内波动幅度",
    "Brent_close_1日差分": "布伦特价格1日差分",
    "Brent_close_7日滚动标准差": "布伦特7日滚动波动率",
    "OVX_3日滚动标准差": "OVX 3日滚动波动率",
    "T5YIE_30日差分": "通胀预期30日变化",
    "T5YIE_30日涨跌幅(%)": "通胀预期30日涨跌幅",
    "T5YIE_趋势标记(1=上升,0=下降)": "通胀预期趋势方向",
    "DXY_7日滚动均值": "美元指数7日均值",
    "Gasoline_7日涨跌幅(%)": "汽油7日涨跌幅",
    "Crack_Spread_3日差分": "裂解价差3日变化",
    "Crack_Spread_趋势标记(1=上升,0=下降)": "裂解价差趋势方向",
    "OVX_滞后1日": "OVX 滞后1日",
    "OVX_滞后3日": "OVX 滞后3日",
    "DXY_滞后1日": "美元指数滞后1日",
    "DXY_滞后7日": "美元指数滞后7日",
    "Brent_Crude(BZ=F)_Volume": "布伦特原油成交量",
    "衰减系数": "时间衰减系数",
}

FACTOR_GROUPS: dict[str, list[str]] = {
    "价格": [
        "Brent_Crude(BZ=F)_Close",
        "WTI_Crude(CL=F)_Close",
        "Gasoline",
    ],
    "波动率": [
        "OVX",
        "OVX_日涨跌幅 (%)",
        "OVX_3日滚动标准差",
        "Brent_当日波动幅度(%)",
        "Brent_close_7日滚动标准差",
    ],
    "宏观": [
        "DXY",
        "T5YIE",
        "T5YIE_30日差分",
        "T5YIE_趋势标记(1=上升,0=下降)",
    ],
    "衍生": [
        "Crack_Spread_3日差分",
        "Crack_Spread_趋势标记(1=上升,0=下降)",
        "衰减系数",
    ],
}


def get_display_name(feature: str) -> str:
    """获取特征的中文展示名称，未找到时返回原名。"""
    return FACTOR_DISPLAY_NAMES.get(feature, feature)


def get_factor_group(feature: str) -> str:
    """获取特征所属分组，未找到时返回"其他"。"""
    for group, features in FACTOR_GROUPS.items():
        if feature in features:
            return group
    return "其他"
