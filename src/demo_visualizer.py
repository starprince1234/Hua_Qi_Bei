"""
可视化模块使用示例
演示如何使用 ModelVisualizer 生成各类图表
"""

import pandas as pd
import numpy as np
import joblib
import sys
import os
from pathlib import Path

# 设置控制台编码
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# 获取项目根目录（src 的父目录）
BASE_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 添加 src 目录到路径
sys.path.insert(0, str(BASE_DIR / 'src'))

from model import StackingModel, OilPricePredictor, BaseModels
from visualizer import ModelVisualizer, quick_plot_prediction, quick_plot_residuals, quick_plot_scatter

# 数据文件映射（与 model.py 保持一致，使用相对路径）
# 注意：这些路径是相对于 src 目录的
DATA_FILES = {
    '1D': '../data/processed/油价预测1日波动率因子表.xlsx',
    '3D': '../data/processed/油价预测3日波动率因子表.xlsx',
    '7D': '../data/processed/油价预测7日波动率因子表.xlsx',
    '14D': '../data/processed/油价预测14日波动率因子表.xlsx',
    '30D': '../data/processed/油价预测30日波动率因子表.xlsx'
}

# 目标变量列名
TARGET_COLS = {
    '1D': 'Brent_close_1日涨跌幅 (%)',
    '3D': 'Brent_close_3日涨跌幅 (%)',
    '7D': 'Brent_close_7日涨跌幅 (%)',
    '14D': 'Brent_close_14日涨跌幅 (%)',
    '30D': 'Brent_close_30日涨跌幅 (%)'
}


# ============================================================
# 方法 1: 使用已保存的模型文件（推荐）
# ============================================================
def demo_with_saved_models():
    """使用已保存的模型进行可视化演示"""
    
    print("="*60)
    print("【演示】使用已保存的模型")
    print("="*60)
    
    # 1. 加载模型（使用绝对路径）
    model_path = BASE_DIR / 'OilPrice_Full_Suite.pkl'
    try:
        models_dict = joblib.load(model_path)
    except Exception as e:
        print(f"✗ 模型加载失败：{e}")
        print("  请先运行 model.py 训练模型")
        print("  或使用选项 2 使用模拟数据演示")
        return

    if not models_dict:
        print("✗ 模型文件为空，请先训练模型")
        print("  运行：python src/model.py")
        print("  或使用选项 2 使用模拟数据演示")
        return

    print(f"✓ 已加载模型：{list(models_dict.keys())}")

    # 2. 准备测试数据（以 7D 周期为例）
    # 使用相对于 src 目录的路径（与 model.py 一致）
    src_dir = Path(__file__).parent  # src 目录
    data_dir = src_dir / '..' / 'data' / 'processed'
    
    # 通过遍历目录获取文件名，避免 Windows 控制台编码问题
    data_file = None
    for f in data_dir.iterdir():
        # 查找 7 日波动率因子表（使用 ASCII 字符匹配）
        if '7' in f.name and '波动率因子表' in f.name:
            data_file = f
            break

    if data_file is None:
        print(f"✗ 数据文件不存在：{DATA_FILES['7D']}")
        print(f"  目录：{data_dir}")
        print("  请确保数据文件存在，或修改为正确的路径")
        return

    try:
        df = pd.read_excel(data_file)
        print(f"✓ 已加载数据：{len(df)} 条记录")
    except Exception as e:
        print(f"✗ 数据加载失败：{e}")
        return

    # 3. 提取特征和目标变量
    # 使用模糊匹配查找目标列（避免编码问题）
    target_col = None
    for col in df.columns:
        # 查找包含 "Brent_close" 和 "7" 和 "涨跌幅" 的列
        if 'Brent_close' in col and '7' in col and '涨跌幅' in col:
            target_col = col
            break
    
    if target_col is None:
        print(f"✗ 未找到目标列，可用列：{df.columns.tolist()}")
        return
    
    cols_to_drop = [target_col, '日期'] if '日期' in df.columns else [target_col]
    X = df.drop(columns=cols_to_drop)
    y = df[target_col]
    
    # 只保留数值列
    X = X.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])
    
    # 4. 获取模型
    model_7d = models_dict['7D']['model']
    print(f"✓ 已获取 7D 周期模型")
    
    # 5. 生成预测
    xgb_pred, ridge_pred = model_7d.base_models.predict(X)
    meta_features = np.column_stack([xgb_pred, ridge_pred])
    y_pred = model_7d.meta_model.predict(meta_features)

    print(f"✓ 已生成预测结果：{len(y_pred)} 条")

    # ============================================================
    # 开始可视化
    # ============================================================
    viz = ModelVisualizer()
    outputs_dir = BASE_DIR / 'outputs' / 'viz'
    # 确保输出目录存在
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # --- 图 1: 预测 vs 实际值对比 ---
    print("\n生成图 1: 预测 vs 实际值对比...")
    viz.plot_prediction_vs_actual(
        y_actual=y,
        y_pred=y_pred,
        horizon='7D',
        save_path=os.path.join(outputs_dir, 'viz_1_prediction_vs_actual.png')
    )

    # --- 图 2: 残差分布图 ---
    print("\n生成图 2: 残差分布图...")
    viz.plot_residual_distribution(
        y_actual=y,
        y_pred=y_pred,
        horizon='7D',
        save_path=os.path.join(outputs_dir, 'viz_2_residual_distribution.png')
    )

    # --- 图 3: 散点回归图 ---
    print("\n生成图 3: 散点回归图...")
    viz.plot_scatter_regression(
        y_actual=y,
        y_pred=y_pred,
        horizon='7D',
        save_path=os.path.join(outputs_dir, 'viz_3_scatter_regression.png')
    )

    # --- 图 4: 特征重要性 ---
    print("\n生成图 4: 特征重要性...")
    viz.plot_feature_importance(
        model=model_7d,
        top_n=15,
        horizon='7D',
        save_path=os.path.join(outputs_dir, 'viz_4_feature_importance.png')
    )

    # --- 图 5: 综合评估报告 ---
    print("\n生成图 5: 综合评估报告...")
    viz.plot_comprehensive_report(
        model=model_7d,
        X_test=X,
        y_test=y,
        horizon='7D',
        save_path=os.path.join(outputs_dir, 'viz_5_comprehensive_report.png')
    )

    print("\n" + "="*60)
    print(f"✓ 所有图表已保存到 {outputs_dir} 目录")
    print("="*60)


# ============================================================
# 方法 2: 使用便捷函数快速绘图
# ============================================================
def demo_quick_plots():
    """使用便捷函数快速绘图"""

    print("\n" + "="*60)
    print("【演示】使用便捷函数快速绘图")
    print("="*60)

    # 模拟数据
    np.random.seed(42)
    n_samples = 100

    # 生成模拟的实际值和预测值
    y_actual = np.random.randn(n_samples) * 2
    y_pred = y_actual + np.random.randn(n_samples) * 0.5

    outputs_dir = BASE_DIR / 'outputs' / 'viz'
    # 确保输出目录存在
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 快速绘图
    quick_plot_prediction(y_actual, y_pred, horizon='1D',
                         save_path=str(outputs_dir / 'quick_1_prediction.png'))

    quick_plot_residuals(y_actual, y_pred, horizon='1D',
                        save_path=str(outputs_dir / 'quick_2_residuals.png'))

    quick_plot_scatter(y_actual, y_pred, horizon='1D',
                      save_path=str(outputs_dir / 'quick_3_scatter.png'))

    print("✓ 便捷函数绘图完成")


# ============================================================
# 方法 2.5: 使用模拟数据演示完整可视化流程
# ============================================================
def demo_with_simulated_data():
    """使用模拟数据演示完整可视化流程（无需真实模型）"""
    
    print("\n" + "="*60)
    print("【演示】使用模拟数据演示完整可视化")
    print("="*60)
    
    # 生成模拟数据
    np.random.seed(42)
    n_samples = 200
    
    # 模拟日期
    dates = pd.date_range(start='2024-01-01', periods=n_samples, freq='D')
    
    # 模拟实际值（类似油价波动）
    trend = np.linspace(0, 10, n_samples)
    noise = np.random.randn(n_samples) * 2
    y_actual = trend + noise
    
    # 模拟预测值（带一些误差）
    y_pred = y_actual + np.random.randn(n_samples) * 1.5
    
    # 创建 DataFrame
    df = pd.DataFrame({
        '日期': dates,
        '实际值': y_actual,
        '预测值': y_pred,
        '残差': y_actual - y_pred
    })
    
    print(f"✓ 生成模拟数据：{n_samples} 条记录")
    
    # 初始化可视化器
    viz = ModelVisualizer()
    outputs_dir = BASE_DIR / 'outputs' / 'viz'
    # 确保输出目录存在
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 1. 预测 vs 实际值对比
    print("\n生成图 1: 预测 vs 实际值对比...")
    viz.plot_prediction_vs_actual_with_date(
        df=df,
        actual_col='实际值',
        pred_col='预测值',
        date_col='日期',
        horizon='7D (模拟)',
        save_path=str(outputs_dir / 'sim_1_prediction_vs_actual.png')
    )

    # 2. 残差分布
    print("生成图 2: 残差分布...")
    viz.plot_residual_distribution(
        y_actual=y_actual,
        y_pred=y_pred,
        horizon='7D (模拟)',
        save_path=str(outputs_dir / 'sim_2_residual_distribution.png')
    )

    # 3. 散点回归
    print("生成图 3: 散点回归...")
    viz.plot_scatter_regression(
        y_actual=y_actual,
        y_pred=y_pred,
        horizon='7D (模拟)',
        save_path=str(outputs_dir / 'sim_3_scatter_regression.png')
    )

    # 4. 残差时序
    print("生成图 4: 残差时序...")
    viz.plot_residual_time_series(
        y_actual=y_actual,
        y_pred=y_pred,
        date_index=dates,
        horizon='7D (模拟)',
        save_path=str(outputs_dir / 'sim_4_residual_timeseries.png')
    )

    # 5. 带密度散点图
    print("生成图 5: 带密度散点图...")
    viz.plot_scatter_with_density(
        y_actual=y_actual,
        y_pred=y_pred,
        horizon='7D (模拟)',
        save_path=str(outputs_dir / 'sim_5_scatter_density.png')
    )
    
    print("\n" + "="*60)
    print(f"✓ 所有模拟图表已保存到 {outputs_dir} 目录")
    print("="*60)


# ============================================================
# 方法 3: 带日期的可视化
# ============================================================
def demo_with_date():
    """带日期的可视化演示"""

    print("\n" + "="*60)
    print("【演示】带日期的可视化")
    print("="*60)

    # 使用相对于 src 目录的路径（与 model.py 一致）
    src_dir = Path(__file__).parent  # src 目录
    data_dir = src_dir / '..' / 'data' / 'processed'
    
    # 通过遍历目录获取文件名，避免 Windows 控制台编码问题
    data_file = None
    for f in data_dir.iterdir():
        if '7' in f.name and '波动率因子表' in f.name:
            data_file = f
            break

    if data_file is None:
        print(f"✗ 数据文件不存在")
        return

    try:
        df = pd.read_excel(data_file)
    except Exception as e:
        print(f"✗ 数据加载失败：{e}")
        return

    # 加载模型
    models_dict = joblib.load(BASE_DIR / 'OilPrice_Full_Suite.pkl')
    model_7d = models_dict['7D']['model']

    # 准备数据
    # 使用模糊匹配查找目标列（避免编码问题）
    target_col = None
    for col in df.columns:
        if 'Brent_close' in col and '7' in col and '涨跌幅' in col:
            target_col = col
            break
    
    if target_col is None:
        print(f"✗ 未找到目标列")
        return

    cols_to_drop = [target_col, '日期'] if '日期' in df.columns else [target_col]
    X = df.drop(columns=cols_to_drop)
    y = df[target_col]
    
    # 只保留数值列
    X = X.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])

    # 生成预测
    xgb_pred, ridge_pred = model_7d.base_models.predict(X)
    meta_features = np.column_stack([xgb_pred, ridge_pred])
    y_pred = model_7d.meta_model.predict(meta_features)

    # 创建包含日期的 DataFrame
    if '日期' in df.columns:
        plot_df = pd.DataFrame({
            '日期': df['日期'],
            '实际值': y.values,
            '预测值': y_pred
        })

        viz = ModelVisualizer()
        viz.plot_prediction_vs_actual_with_date(
            df=plot_df,
            actual_col='实际值',
            pred_col='预测值',
            horizon='7D',
            date_col='日期',
            save_path=str(BASE_DIR / 'outputs' / 'viz_with_date.png')
        )

    print("✓ 带日期的可视化完成")


# ============================================================
# 方法 4: 多周期对比
# ============================================================
def demo_multi_horizon_comparison():
    """多周期模型对比"""

    print("\n" + "="*60)
    print("【演示】多周期特征重要性对比")
    print("="*60)

    # 加载所有模型
    models_dict = joblib.load(BASE_DIR / 'OilPrice_Full_Suite.pkl')

    # 提取模型对象
    models = {k: v['model'] for k, v in models_dict.items()}

    viz = ModelVisualizer()
    viz.plot_feature_importance_comparison(
        models_dict=models,
        top_n=15,
        save_path=str(BASE_DIR / 'outputs' / 'multi_horizon_comparison.png')
    )

    print("✓ 多周期对比完成")


# ============================================================
# 方法 5: 风险区间可视化
# ============================================================
def demo_risk_interval():
    """风险区间可视化演示"""

    print("\n" + "="*60)
    print("【演示】风险区间可视化")
    print("="*60)

    # 使用相对于 src 目录的路径（与 model.py 一致）
    src_dir = Path(__file__).parent  # src 目录
    data_dir = src_dir / '..' / 'data' / 'processed'
    
    # 通过遍历目录获取文件名，避免 Windows 控制台编码问题
    data_file = None
    for f in data_dir.iterdir():
        if '7' in f.name and '波动率因子表' in f.name:
            data_file = f
            break

    if data_file is None:
        print(f"✗ 数据文件不存在")
        return

    try:
        df = pd.read_excel(data_file)
    except Exception as e:
        print(f"✗ 数据加载失败：{e}")
        return

    # 加载模型
    models_dict = joblib.load(BASE_DIR / 'OilPrice_Full_Suite.pkl')
    model_7d = models_dict['7D']['model']

    # 准备数据
    # 使用模糊匹配查找目标列（避免编码问题）
    target_col = None
    for col in df.columns:
        if 'Brent_close' in col and '7' in col and '涨跌幅' in col:
            target_col = col
            break
    
    if target_col is None:
        print(f"✗ 未找到目标列")
        return

    cols_to_drop = [target_col, '日期'] if '日期' in df.columns else [target_col]
    X = df.drop(columns=cols_to_drop)
    
    # 只保留数值列
    X = X.select_dtypes(include=['int64', 'float64', 'int32', 'float32'])

    # 假设当前价格
    current_price = 80.0  # 美元/桶

    # 生成带风险区间的预测
    predictions = []
    for idx in range(min(20, len(X))):  # 只演示前 20 个样本
        X_sample = X.iloc[idx:idx+1]
        result = model_7d.predict_with_risk(X_sample, current_price)
        predictions.append(result)
        current_price = result['predicted_price']  # 更新当前价格

    # 整理预测结果
    pred_dict = {
        'predicted_price': [p['predicted_price'] for p in predictions],
        'risk_interval': [p['risk_interval'] for p in predictions]
    }

    viz = ModelVisualizer()
    viz.plot_risk_interval(
        predictions_dict=pred_dict,
        save_path=str(BASE_DIR / 'outputs' / 'risk_interval_demo.png')
    )

    print("✓ 风险区间可视化完成")


# ============================================================
# 主函数
# ============================================================
if __name__ == '__main__':
    import sys

    # 确保输出目录存在
    outputs_dir = BASE_DIR / 'outputs' / 'viz'
    outputs_dir.mkdir(parents=True, exist_ok=True)

    # 选择要运行的演示
    print("\n请选择要运行的演示：")
    print("1. 使用已保存的模型完整演示（需要先训练模型）")
    print("2. 使用模拟数据演示完整可视化流程（推荐）")
    print("3. 便捷函数快速绘图（使用模拟数据）")
    print("4. 带日期的可视化")
    print("5. 多周期对比")
    print("6. 风险区间可视化")
    print("7. 运行所有演示")
    
    # 支持命令行参数或交互式输入
    if len(sys.argv) > 1:
        choice = sys.argv[1]
        print(f"\n自动选择选项：{choice}")
    else:
        try:
            choice = input("\n请输入选项 (1-7): ").strip()
        except (EOFError, KeyboardInterrupt):
            # 非交互式环境默认运行选项 2（模拟数据）
            choice = '2'
            print(f"\n非交互式模式，自动选择选项：{choice}")
    
    if choice == '1':
        demo_with_saved_models()
    elif choice == '2':
        demo_with_simulated_data()
    elif choice == '3':
        demo_quick_plots()
    elif choice == '4':
        demo_with_date()
    elif choice == '5':
        demo_multi_horizon_comparison()
    elif choice == '6':
        demo_risk_interval()
    elif choice == '7':
        demo_with_simulated_data()
        demo_quick_plots()
        print("\n" + "="*60)
        print("✓ 所有演示已完成！")
        print("="*60)
    else:
        print("无效的选项")
