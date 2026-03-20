import pandas as pd
import numpy as np
import openai
import json
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

# ==================== 1. 基础配置 ====================
AUTOdl_BASE_URL = "http://127.0.0.1:6006/v1"
AUTOdl_API_KEY = "eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOjkxMjU3MiwidXVpZCI6IjVjMzU5NTljOWUxZTVlZDIiLCJpc19hZG1pbiI6ZmFsc2UsImJhY2tzdGFnZV9yb2xlIjoiIiwiaXNfc3VwZXJfYWRtaW4iOmZhbHNlLCJzdWJfbmFtZSI6IiIsInRlbmFudCI6ImF1dG9kbCIsInVwayI6IiJ9.-cRCRh4CP3VFpoZ7_BroBGkFA7B03e_IcGqkhL4pUNz-S0JGVeM7-xT9krC03MUGFB4UixMqD6MM7EnNs9xjuA"

# 🔥 修正：7日波动率仅保留 11 个输入因子（移除了作为目标变量的 7日涨跌幅）
VOLATILITY_FEATURE_MAP = {
    "1日波动率": ["Brent_Crude(BZ=F)_Close", "OVX_日涨跌幅 (%)", "Gasoline_7日涨跌幅(%)",
                  "T5YIE_趋势标记(1=上升,0=下降)"],
    "3日波动率": ["Gasoline_7日涨跌幅(%)", "Brent_close_1日差分", "OVX_日涨跌幅 (%)", "T5YIE_趋势标记(1=上升,0=下降)",
                  "T5YIE_30日差分", "Crack_Spread_3日差分"],
    "7日波动率": [
        "Gasoline_7日涨跌幅(%)",
        "Brent_close_1日差分",
        "T5YIE_趋势标记(1=上升,0=下降)",
        "T5YIE_30日差分",
        "OVX_3日滚动标准差",
        "OVX_日涨跌幅 (%)",
        "Brent_当日波动幅度(%)",
        "OVX",
        "T5YIE_30日涨跌幅(%)",
        "Crack_Spread_趋势标记(1=上升,0=下降)",
        "衰减系数"
    ],
    "14日波动率": ["Gasoline_7日涨跌幅(%)", "T5YIE_30日差分", "T5YIE_趋势标记(1=上升,0=下降)", "T5YIE_30日涨跌幅(%)",
                   "OVX_3日滚动标准差", "Brent_close_1日差分", "OVX", "Brent_当日波动幅度(%)", "OVX_滞后1日", "DXY",
                   "DXY_滞后1日", "DXY_7日滚动均值", "OVX_滞后3日", "Brent_close_7日滚动标准差", "DXY_滞后7日",
                   "OVX_日涨跌幅 (%)"],
    "30日波动率": ["T5YIE_30日差分", "T5YIE_30日涨跌幅(%)", "T5YIE_趋势标记(1=上升,0=下降)", "Gasoline_7日涨跌幅(%)",
                   "OVX", "OVX_滞后1日", "Brent_当日波动幅度(%)", "OVX_滞后3日", "DXY", "DXY_滞后1日",
                   "DXY_7日滚动均值", "OVX_3日滚动标准差", "DXY_滞后7日", "Brent_close_1日差分",
                   "WTI_Crude(CL=F)_Close", "Brent_close_7日滚动标准差", "Brent_Crude(BZ=F)_Close", "T5YIE", "Gasoline",
                   "Brent_Crude(BZ=F)_Volume"]
}


# ==================== 2. 预测逻辑 ====================

def run_multi_horizon_prediction(input_excel_path):
    print(f"📖 正在加载待预测数据: {input_excel_path}")
    try:
        df_input = pd.read_excel(input_excel_path)
    except Exception as e:
        print(f"❌ 读取 Excel 失败: {e}")
        return

    last_row = df_input.iloc[-1]

    # 提取当前价格作为预测基准
    current_price = float(last_row.get("Brent_Crude(BZ=F)_Close", 0.0))

    # 1. 提取因子负载包
    filtered_features_payload = {}
    for vol_type, required_cols in VOLATILITY_FEATURE_MAP.items():
        vals = []
        for col in required_cols:
            actual_col = col
            # DXY 命名兼容
            if col == "DXY_7日滞后" and "DXY_滞后7日" in last_row:
                actual_col = "DXY_滞后7日"

            val = last_row.get(actual_col, 0.0)
            if pd.isna(val) or val == "":
                val = 0.0
            vals.append(float(val))
        filtered_features_payload[vol_type] = vals

    # 2. 调用云端 API
    print(f"📡 正在发送全因子请求至云端预测服务器...")
    client = openai.OpenAI(api_key=AUTOdl_API_KEY, base_url=AUTOdl_BASE_URL)

    request_body = {
        "task_type": "oil_volatility_prediction",
        "filtered_features": filtered_features_payload,
        "volatility_feature_map": VOLATILITY_FEATURE_MAP,
        "current_price": current_price
    }

    try:
        response = client.chat.completions.create(
            model="oil_vol_model",
            messages=[{"role": "user", "content": json.dumps(request_body, ensure_ascii=False)}],
            temperature=0.0
        )

        res_content = json.loads(response.choices[0].message.content)
        vol_results = res_content.get("volatility_results", [])

        # 错误诊断
        for r in vol_results:
            if r.get("status") == "failed":
                print(f"⚠️ {r['volatility_type']} 预测失败! 原因: {r.get('error')}")

        # 3. 整理输出数据
        order = ["1日波动率", "3日波动率", "7日波动率", "14日波动率", "30日波动率"]
        res_lookup = {item["volatility_type"]: item for item in vol_results}

        final_rows = []
        for vol_name in order:
            data = res_lookup.get(vol_name, {})
            risk = data.get("risk_interval", [np.nan, np.nan])

            final_rows.append({
                "周期": vol_name,
                "预测涨跌幅(%)": data.get("predicted_return", np.nan),
                "预测绝对价格": data.get("predicted_price", np.nan),
                "风险区间下限": risk[0] if len(risk) == 2 else np.nan,
                "风险区间上限": risk[1] if len(risk) == 2 else np.nan
            })

        df_output = pd.DataFrame(final_rows)
        output_filename = f"多周期预测结果_{datetime.now().strftime('%m%d%H%M')}.xlsx"
        df_output.to_excel(output_filename, index=False)

        print(f"\n✅ 处理完成！")
        print(f"📂 结果已保存至: {output_filename}")
        print("-" * 65)
        print(df_output.to_string(index=False))
        print("-" * 65)

    except Exception as e:
        print(f"❌ 调用失败: {e}")


if __name__ == "__main__":
    run_multi_horizon_prediction("../data/raw/test1.xlsx")
