"""
油价预测系统 - 可视化模块
用于模型评估、特征分析、预测结果展示
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import joblib
import warnings
warnings.filterwarnings('ignore')

# 设置样式
sns.set_style("whitegrid")
sns.set_context("notebook", font_scale=1.0)

# 设置中文字体 - 必须在 seaborn 设置之后
# SimHei (黑体) 是 Windows 系统自带中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']  # 指定默认中文字体
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题

# 强制刷新字体设置
plt.rcParams['font.family'] = 'sans-serif'


class ModelVisualizer:
    """模型可视化器"""

    def __init__(self, models=None):
        """
        初始化可视化器

        Args:
            models: 模型字典，格式为 {horizon: model_dict}
        """
        self.models = models or {}
        self.results = {}

    # ============================================================
    # 类型 1: 预测 vs 实际值对比图
    # ============================================================
    def plot_prediction_vs_actual(self, y_actual, y_pred, horizon='1D',
                                   title=None, save_path=None, figsize=(12, 6)):
        """预测值 vs 实际值对比图（折线图）"""
        fig, ax = plt.subplots(figsize=figsize)

        ax.plot(y_actual.values if hasattr(y_actual, 'values') else y_actual,
                label='实际值', color='#2E86AB', linewidth=1.5, marker='o', markersize=3)
        ax.plot(y_pred, label='预测值', color='#A23B72', linewidth=1.5,
                linestyle='--', marker='s', markersize=3)

        r2 = r2_score(y_actual, y_pred)
        rmse = np.sqrt(mean_squared_error(y_actual, y_pred))
        mae = mean_absolute_error(y_actual, y_pred)

        ax.set_xlabel('样本索引', fontsize=12)
        ax.set_ylabel('涨跌幅 (%)', fontsize=12)
        ax.set_title(title or f'【{horizon}】预测值 vs 实际值对比\n'
                     f'={r2:.4f}, RMSE={rmse:.4f}, MAE={mae:.4f}',
                     fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    def plot_prediction_vs_actual_with_date(self, df, actual_col, pred_col,
                                             horizon='1D', date_col=None,
                                             save_path=None, figsize=(14, 7)):
        """带日期的预测值 vs 实际值对比图"""
        fig, ax = plt.subplots(figsize=figsize)

        if date_col and date_col in df.columns:
            x_values = pd.to_datetime(df[date_col])
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            x_values = range(len(df))

        ax.plot(x_values, df[actual_col].values, label='实际值',
                color='#2E86AB', linewidth=1.5, alpha=0.8)
        ax.plot(x_values, df[pred_col].values, label='预测值',
                color='#A23B72', linewidth=1.5, alpha=0.8, linestyle='--')
        ax.fill_between(x_values, df[actual_col].values, df[pred_col].values,
                        alpha=0.2, color='gray', label='误差区域')

        r2 = r2_score(df[actual_col], df[pred_col])
        rmse = np.sqrt(mean_squared_error(df[actual_col], df[pred_col]))
        mae = mean_absolute_error(df[actual_col], df[pred_col])
        hit_rate = np.sum(np.sign(df[actual_col].values) ==
                         np.sign(df[pred_col].values)) / len(df) * 100

        ax.set_xlabel('日期' if date_col else '样本索引', fontsize=12)
        ax.set_ylabel('涨跌幅 (%)', fontsize=12)
        ax.set_title(f'【{horizon}】预测值 vs 实际值对比\n'
                     f'R2={r2:.4f}, RMSE={rmse:.4f}, MAE={mae:.4f}, 方向准确率={hit_rate:.1f}%',
                     fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    # ============================================================
    # 类型 2: 残差分布图（直方图+Q-Q 图）
    # ============================================================
    def plot_residual_distribution(self, y_actual, y_pred, horizon='1D',
                                    save_path=None, figsize=(14, 6)):
        """残差分布图：直方图 + KDE + Q-Q 图"""
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(1, 2, figure=fig, width_ratios=[1, 1])

        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])

        residuals = np.array(y_actual) - np.array(y_pred)

        # 左图：残差直方图 + KDE
        sns.histplot(residuals, kde=True, ax=ax1, color='#3498DB',
                     bins=30, stat='density', alpha=0.7)
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2, label='零线')

        mu, sigma = np.mean(residuals), np.std(residuals)
        x_norm = np.linspace(residuals.min(), residuals.max(), 100)
        from scipy import stats
        ax1.plot(x_norm, stats.norm.pdf(x_norm, mu, sigma),
                 'r-', linewidth=2, label=f'正态拟合 (μ={mu:.4f}, σ={sigma:.4f})')

        ax1.set_xlabel('残差', fontsize=12)
        ax1.set_ylabel('密度', fontsize=12)
        ax1.set_title(f'【{horizon}】残差分布直方图', fontsize=13, pad=10)
        ax1.legend(loc='best', fontsize=9)
        ax1.grid(True, alpha=0.3)

        # 右图：Q-Q 图
        stats.probplot(residuals, dist="norm", plot=ax2)
        ax2.set_title(f'【{horizon}】残差 Q-Q 图', fontsize=13, pad=10)
        ax2.set_xlabel('理论分位数', fontsize=11)
        ax2.set_ylabel('实际分位数', fontsize=11)
        ax2.grid(True, alpha=0.3)

        stats_text = (f'均值：{np.mean(residuals):.6f}\n'
                      f'标准差：{np.std(residuals):.6f}\n'
                      f'偏度：{stats.skew(residuals):.4f}\n'
                      f'峰度：{stats.kurtosis(residuals):.4f}')
        ax2.text(0.02, 0.98, stats_text, transform=ax2.transAxes,
                 fontsize=9, verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, (ax1, ax2)

    def plot_residual_time_series(self, y_actual, y_pred, date_index=None,
                                   horizon='1D', save_path=None, figsize=(14, 6)):
        """残差时序图：展示残差随时间的变化"""
        fig, ax = plt.subplots(figsize=figsize)
        residuals = np.array(y_actual) - np.array(y_pred)

        has_date_index = date_index is not None and len(date_index) > 0

        if has_date_index:
            x_values = pd.to_datetime(date_index)
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        else:
            x_values = range(len(residuals))

        ax.bar(x_values, residuals, color=np.where(residuals >= 0, '#27AE60', '#E74C3C'),
               alpha=0.7, label='残差')
        ax.axhline(y=0, color='black', linestyle='-', linewidth=1)

        std_res = np.std(residuals)
        ax.axhline(y=2*std_res, color='orange', linestyle='--',
                   linewidth=1.5, label=f'+2σ ({2*std_res:.4f})')
        ax.axhline(y=-2*std_res, color='orange', linestyle='--',
                   linewidth=1.5, label=f'-2σ ({-2*std_res:.4f})')

        ax.set_xlabel('日期' if has_date_index else '样本索引', fontsize=12)
        ax.set_ylabel('残差', fontsize=12)
        ax.set_title(f'【{horizon}】残差时序图', fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    # ============================================================
    # 类型 3: 特征重要性热力图
    # ============================================================
    def plot_feature_importance(self, model, top_n=20, horizon='1D',
                                 save_path=None, figsize=(10, 8)):
        """特征重要性条形图（TOP N）"""
        fig, ax = plt.subplots(figsize=figsize)

        importance_df = model.get_feature_importance(top_n=top_n)

        if importance_df is None or len(importance_df) == 0:
            print("✗ 无法获取特征重要性")
            return fig, ax

        importance_df = importance_df.iloc[::-1]

        bars = ax.barh(importance_df['feature'], importance_df['importance'],
                       color=plt.cm.viridis(np.linspace(0.3, 0.9, len(importance_df))))

        ax.set_xlabel('重要性', fontsize=12)
        ax.set_title(f'【{horizon}】特征重要性 TOP{top_n}', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3, axis='x')

        for bar, val in zip(bars, importance_df['importance']):
            ax.text(bar.get_width() + 0.001, bar.get_y() + bar.get_height()/2,
                   f'{val:.4f}', va='center', fontsize=8)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    def plot_feature_importance_comparison(self, models_dict, top_n=15,
                                            save_path=None, figsize=(12, 8)):
        """多周期特征重要性对比热力图"""
        fig, ax = plt.subplots(figsize=figsize)

        all_importances = {}
        all_features = set()

        for horizon, model in models_dict.items():
            imp_df = model.get_feature_importance(top_n=top_n)
            if imp_df is not None:
                all_importances[horizon] = imp_df.set_index('feature')['importance'].to_dict()
                all_features.update(imp_df['feature'].values)

        if not all_importances:
            print("✗ 无法获取特征重要性")
            return fig, ax

        features = list(all_features)[:top_n]
        heatmap_data = pd.DataFrame(index=features)

        for horizon, imp_dict in all_importances.items():
            heatmap_data[horizon] = [imp_dict.get(f, 0) for f in features]

        sns.heatmap(heatmap_data.T, annot=True, fmt='.4f', cmap='YlOrRd',
                    ax=ax, cbar_kws={'label': '重要性'}, linewidths=0.5)

        ax.set_xlabel('特征', fontsize=12)
        ax.set_ylabel('预测周期', fontsize=12)
        ax.set_title('多周期特征重要性对比', fontsize=14, pad=15)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    # ============================================================
    # 类型 4: 散点回归图
    # ============================================================
    def plot_scatter_regression(self, y_actual, y_pred, horizon='1D',
                                 save_path=None, figsize=(8, 8)):
        """预测值 vs 实际值散点回归图"""
        fig, ax = plt.subplots(figsize=figsize)

        y_actual = np.array(y_actual)
        y_pred = np.array(y_pred)

        r2 = r2_score(y_actual, y_pred)
        rmse = np.sqrt(mean_squared_error(y_actual, y_pred))
        mae = mean_absolute_error(y_actual, y_pred)

        ax.scatter(y_actual, y_pred, c='#3498DB', alpha=0.5,
                   s=30, edgecolors='white', linewidth=0.5)

        min_val = min(y_actual.min(), y_pred.min())
        max_val = max(y_actual.max(), y_pred.max())
        ax.plot([min_val, max_val], [min_val, max_val],
                'r--', linewidth=2, label='理想拟合线 (y=x)')

        z = np.polyfit(y_actual, y_pred, 1)
        p = np.poly1d(z)
        ax.plot(y_actual, p(y_actual), 'g-', linewidth=2,
                label=f'拟合线 (y={z[0]:.4f}x+{z[1]:.4f})')

        ax.set_xlabel('实际值', fontsize=12)
        ax.set_ylabel('预测值', fontsize=12)
        ax.set_title(f'【{horizon}】预测值 vs 实际值散点图\n'
                     f'R2={r2:.4f}, RMSE={rmse:.4f}, MAE={mae:.4f}',
                     fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        stats_text = (f'R2 = {r2:.4f}\n'
                      f'RMSE = {rmse:.4f}\n'
                      f'MAE = {mae:.4f}\n'
                      f'斜率 = {z[0]:.4f}\n'
                      f'截距 = {z[1]:.4f}')
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=10, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    def plot_scatter_with_density(self, y_actual, y_pred, horizon='1D',
                                   save_path=None, figsize=(8, 8)):
        """带密度等值线的散点回归图"""
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(2, 2, figure=fig, width_ratios=[4, 1], height_ratios=[1, 4],
                      wspace=0.05, hspace=0.05)

        ax_main = fig.add_subplot(gs[1, 0])
        ax_top = fig.add_subplot(gs[0, 0], sharex=ax_main)
        ax_right = fig.add_subplot(gs[1, 1], sharey=ax_main)

        y_actual = np.array(y_actual)
        y_pred = np.array(y_pred)

        r2 = r2_score(y_actual, y_pred)

        from scipy.stats import gaussian_kde
        xy = np.vstack([y_actual, y_pred])
        z = gaussian_kde(xy)(xy)
        idx = z.argsort()

        ax_main.scatter(y_actual[idx], y_pred[idx], c=z[idx],
                        cmap='viridis', s=20, alpha=0.6)

        min_val = min(y_actual.min(), y_pred.min())
        max_val = max(y_actual.max(), y_pred.max())
        ax_main.plot([min_val, max_val], [min_val, max_val],
                     'r--', linewidth=2, label='理想拟合线 (y=x)')

        ax_main.set_xlabel('实际值', fontsize=11)
        ax_main.set_ylabel('预测值', fontsize=11)
        ax_main.set_title(f'【{horizon}】密度散点图 (R2={r2:.4f})', fontsize=12)
        ax_main.legend(loc='best', fontsize=9)
        ax_main.grid(True, alpha=0.3)

        sns.kdeplot(y_actual, ax=ax_top, fill=True, color='#2E86AB', alpha=0.5)
        ax_top.set_ylabel('密度', fontsize=9)
        ax_top.set_title('实际值分布', fontsize=10)
        ax_top.grid(True, alpha=0.3)
        plt.setp(ax_top.get_xticklabels(), visible=False)
        ax_top.tick_params(axis='y', labelsize=8)

        # 修复：使用垂直 KDE 绘图，兼容不同 seaborn 版本
        try:
            sns.kdeplot(y_pred, ax=ax_right, fill=True, color='#A23B72', alpha=0.5,
                        orient='y')
        except (TypeError, AttributeError) as e:
            # 旧版本 seaborn 不支持 orient 参数，使用替代方法
            y_pred_sorted = np.sort(y_pred)
            y_pred_density = np.linspace(0, 1, len(y_pred_sorted))
            ax_right.fill_betweenx(y_pred_sorted, 0, y_pred_density,
                                   color='#A23B72', alpha=0.5)
        ax_right.set_xlabel('密度', fontsize=9)
        ax_right.set_title('预测值分布', fontsize=10)
        ax_right.grid(True, alpha=0.3)
        plt.setp(ax_right.get_yticklabels(), visible=False)
        ax_right.tick_params(axis='x', labelsize=8)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, (ax_main, ax_top, ax_right)

    # ============================================================
    # 类型 5: 风险区间可视化
    # ============================================================
    def plot_risk_interval(self, predictions_dict, actual_prices=None,
                            save_path=None, figsize=(14, 7)):
        """
        风险区间可视化：展示预测价格的上下区间

        Args:
            predictions_dict: 预测结果字典，包含 'predicted_price', 'risk_interval'
            actual_prices: 实际价格序列（可选）
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, ax = plt.subplots(figsize=figsize)

        pred_prices = predictions_dict.get('predicted_price', [])
        risk_intervals = predictions_dict.get('risk_interval', [])
        indices = range(len(pred_prices))

        # 提取上下界
        lower_bounds = [interval[0] for interval in risk_intervals]
        upper_bounds = [interval[1] for interval in risk_intervals]

        # 绘制风险区间
        ax.fill_between(indices, lower_bounds, upper_bounds,
                        alpha=0.3, color='gray', label='风险区间 (90% CI)')

        # 绘制预测价格
        ax.plot(indices, pred_prices, 'b-', linewidth=2, marker='o',
                markersize=5, label='预测价格')

        # 绘制实际价格（如果有）
        if actual_prices is not None:
            ax.plot(indices, actual_prices, 'r-', linewidth=2, marker='s',
                    markersize=5, label='实际价格')

        ax.set_xlabel('预测期', fontsize=12)
        ax.set_ylabel('价格', fontsize=12)
        ax.set_title('油价预测风险区间', fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    def plot_prediction_with_uncertainty(self, df, date_col, pred_col,
                                          lower_col, upper_col,
                                          actual_col=None, horizon='1D',
                                          save_path=None, figsize=(14, 7)):
        """
        带不确定性区间的预测图

        Args:
            df: 包含预测结果的 DataFrame
            date_col: 日期列名
            pred_col: 预测值列名
            lower_col: 下界列名
            upper_col: 上界列名
            actual_col: 实际值列名（可选）
            horizon: 预测周期
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, ax = plt.subplots(figsize=figsize)

        x_values = pd.to_datetime(df[date_col])

        # 绘制不确定性区间
        ax.fill_between(x_values, df[lower_col], df[upper_col],
                        alpha=0.3, color='gray', label='不确定性区间')

        # 绘制预测值
        ax.plot(x_values, df[pred_col], 'b-', linewidth=2,
                label='预测值', marker='o', markersize=4)

        # 绘制实际值（如果有）
        if actual_col and actual_col in df.columns:
            ax.plot(x_values, df[actual_col], 'r-', linewidth=2,
                    label='实际值', marker='s', markersize=4)

        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格/涨跌幅', fontsize=12)
        ax.set_title(f'【{horizon}】预测结果与不确定性区间', fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    # ============================================================
    # 类型 6: 学习曲线
    # ============================================================
    def plot_learning_curve(self, train_scores, val_scores, train_sizes=None,
                            title='学习曲线', save_path=None, figsize=(10, 6)):
        """
        学习曲线：展示训练集和验证集性能随样本数的变化

        Args:
            train_scores: 训练集得分列表
            val_scores: 验证集得分列表
            train_sizes: 训练样本数列表（可选）
            title: 图表标题
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, ax = plt.subplots(figsize=figsize)

        if train_sizes is None:
            train_sizes = range(1, len(train_scores) + 1)

        # 计算统计量
        train_mean = np.mean(train_scores, axis=1) if len(np.array(train_scores).shape) > 1 else train_scores
        train_std = np.std(train_scores, axis=1) if len(np.array(train_scores).shape) > 1 else np.zeros_like(train_scores)
        val_mean = np.mean(val_scores, axis=1) if len(np.array(val_scores).shape) > 1 else val_scores
        val_std = np.std(val_scores, axis=1) if len(np.array(val_scores).shape) > 1 else np.zeros_like(val_scores)

        # 绘制学习曲线
        ax.plot(train_sizes, train_mean, 'o-', color='#3498DB',
                linewidth=2, label='训练集得分')
        ax.fill_between(train_sizes, train_mean - train_std, train_mean + train_std,
                        alpha=0.15, color='#3498DB')

        ax.plot(train_sizes, val_mean, 's-', color='#E74C3C',
                linewidth=2, label='验证集得分')
        ax.fill_between(train_sizes, val_mean - val_std, val_mean + val_std,
                        alpha=0.15, color='#E74C3C')

        ax.set_xlabel('训练样本数', fontsize=12)
        ax.set_ylabel('R2 得分', fontsize=12)
        ax.set_title(title, fontsize=14, pad=15)
        ax.legend(loc='best', fontsize=10)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    def plot_metrics_comparison(self, metrics_dict, save_path=None, figsize=(10, 6)):
        """
        多模型指标对比柱状图

        Args:
            metrics_dict: 模型指标字典 {model_name: {'R2': x, 'RMSE': y, ...}}
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, axes = plt.subplots(1, 2, figsize=figsize)

        model_names = list(metrics_dict.keys())
        r2_scores = [metrics_dict[m]['R2'] for m in model_names]
        rmse_scores = [metrics_dict[m]['RMSE'] for m in model_names]

        # R2 对比
        colors = plt.cm.viridis(np.linspace(0.3, 0.9, len(model_names)))
        axes[0].bar(model_names, r2_scores, color=colors, alpha=0.8)
        axes[0].set_ylabel('R2', fontsize=12)
        axes[0].set_title('R2 对比', fontsize=13)
        axes[0].grid(True, alpha=0.3, axis='y')

        # RMSE 对比
        axes[1].bar(model_names, rmse_scores, color=colors, alpha=0.8)
        axes[1].set_ylabel('RMSE', fontsize=12)
        axes[1].set_title('RMSE 对比', fontsize=13)
        axes[1].grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, axes

    # ============================================================
    # 类型 7: SHAP 值分析（简化版，使用特征重要性替代）
    # ============================================================
    def plot_shap_summary(self, model, X_sample, horizon='1D',
                          save_path=None, figsize=(10, 8)):
        """
        SHAP 值摘要图（简化版：使用特征重要性 + 偏依赖）

        Args:
            model: StackingModel 实例
            X_sample: 样本特征 DataFrame
            horizon: 预测周期标签
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, axes = plt.subplots(2, 1, figsize=figsize)

        # 上图：特征重要性
        importance_df = model.get_feature_importance(top_n=15)
        if importance_df is not None:
            importance_df = importance_df.iloc[::-1]
            axes[0].barh(importance_df['feature'], importance_df['importance'],
                        color='#3498DB', alpha=0.8)
            axes[0].set_xlabel('重要性', fontsize=11)
            axes[0].set_title(f'【{horizon}】特征重要性', fontsize=12, pad=10)
            axes[0].grid(True, alpha=0.3, axis='x')

        # 下图：特征统计分布
        if X_sample is not None:
            top_features = importance_df['feature'].head(10).tolist() if importance_df is not None else X_sample.columns[:10].tolist()
            X_top = X_sample[top_features]

            # 创建箱线图
            X_top.boxplot(ax=axes[1], rot=45)
            axes[1].set_title('Top 特征分布箱线图', fontsize=12, pad=10)
            axes[1].grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, axes

    def plot_feature_effect(self, model, X, feature_name, horizon='1D',
                            save_path=None, figsize=(10, 6)):
        """
        特征效应图（偏依赖图简化版）

        Args:
            model: StackingModel 实例
            X: 特征 DataFrame
            feature_name: 目标特征名
            horizon: 预测周期标签
            save_path: 保存路径
            figsize: 图表大小
        """
        fig, ax = plt.subplots(figsize=figsize)

        if model.base_models is None or model.base_models.xgb_model is None:
            print("✗ 模型未训练")
            return fig, ax

        # 按特征分箱计算平均预测值
        X_temp = X.copy()
        X_temp['pred'] = model.base_models.xgb_model.predict(X)

        # 分箱
        X_temp['feature_binned'] = pd.qcut(X_temp[feature_name], q=10, duplicates='drop')
        grouped = X_temp.groupby('feature_binned')[['pred', feature_name]].mean()

        # 绘制
        ax.plot(grouped[feature_name], grouped['pred'], 'o-',
                color='#3498DB', linewidth=2, markersize=8)
        ax.set_xlabel(feature_name, fontsize=12)
        ax.set_ylabel('平均预测值', fontsize=12)
        ax.set_title(f'【{horizon}】{feature_name} 特征效应图', fontsize=14, pad=15)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, ax

    # ============================================================
    # 综合报告
    # ============================================================
    def plot_comprehensive_report(self, model, X_test, y_test, horizon='1D',
                                   save_path=None, figsize=(16, 12)):
        """
        综合评估报告：包含多个子图

        Args:
            model: StackingModel 实例
            X_test: 测试集特征
            y_test: 测试集实际值
            horizon: 预测周期标签
            save_path: 保存路径
            figsize: 图表大小
        """
        fig = plt.figure(figsize=figsize)
        gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.25)

        # 获取预测
        xgb_pred, ridge_pred = model.base_models.predict(X_test)
        meta_features = np.column_stack([xgb_pred, ridge_pred])
        y_pred = model.meta_model.predict(meta_features)

        # 图 1: 预测 vs 实际
        ax1 = fig.add_subplot(gs[0, 0])
        ax1.plot(y_test.values if hasattr(y_test, 'values') else y_test,
                label='实际值', color='#2E86AB', linewidth=1.5)
        ax1.plot(y_pred, label='预测值', color='#A23B72', linewidth=1.5, linestyle='--')
        ax1.set_title(f'【{horizon}】预测对比', fontsize=12)
        ax1.legend(fontsize=9)
        ax1.grid(True, alpha=0.3)

        # 图 2: 散点回归
        ax2 = fig.add_subplot(gs[0, 1])
        ax2.scatter(y_test, y_pred, alpha=0.5, c='#3498DB', s=20)
        min_val = min(np.min(y_test), np.min(y_pred))
        max_val = max(np.max(y_test), np.max(y_pred))
        ax2.plot([min_val, max_val], [min_val, max_val], 'r--')
        ax2.set_xlabel('实际值', fontsize=10)
        ax2.set_ylabel('预测值', fontsize=10)
        ax2.set_title(f'散点图 (R2={r2_score(y_test, y_pred):.4f})', fontsize=12)
        ax2.grid(True, alpha=0.3)

        # 图 3: 残差分布
        ax3 = fig.add_subplot(gs[0, 2])
        residuals = np.array(y_test) - y_pred
        sns.histplot(residuals, kde=True, ax=ax3, color='#3498DB', bins=20)
        ax3.axvline(x=0, color='red', linestyle='--')
        ax3.set_title('残差分布', fontsize=12)
        ax3.grid(True, alpha=0.3)

        # 图 4: 特征重要性
        ax4 = fig.add_subplot(gs[1, 0])
        importance_df = model.get_feature_importance(top_n=10)
        if importance_df is not None:
            importance_df = importance_df.iloc[::-1]
            ax4.barh(importance_df['feature'], importance_df['importance'],
                    color=plt.cm.viridis(np.linspace(0.3, 0.9, len(importance_df))))
            ax4.set_title('特征重要性 TOP10', fontsize=12)
            ax4.grid(True, alpha=0.3, axis='x')

        # 图 5: 残差时序
        ax5 = fig.add_subplot(gs[1, 1])
        ax5.bar(range(len(residuals)), residuals,
               color=np.where(residuals >= 0, '#27AE60', '#E74C3C'), alpha=0.7)
        ax5.axhline(y=0, color='black', linestyle='-', linewidth=1)
        ax5.set_title('残差时序', fontsize=12)
        ax5.grid(True, alpha=0.3)

        # 图 6: 指标汇总
        ax6 = fig.add_subplot(gs[1, 2])
        ax6.axis('off')
        r2 = r2_score(y_test, y_pred)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
        mae = mean_absolute_error(y_test, y_pred)
        mape = np.mean(np.abs((y_test - y_pred) / (np.abs(y_test) + 0.001))) * 100
        hit_rate = np.sum(np.sign(y_test) == np.sign(y_pred)) / len(y_test) * 100

        summary_text = (f'【{horizon}】模型评估指标\n\n'
                       f'R2 = {r2:.4f}\n'
                       f'RMSE = {rmse:.4f}\n'
                       f'MAE = {mae:.4f}\n'
                       f'MAPE = {mape:.2f}%\n'
                       f'方向准确率 = {hit_rate:.1f}%')
        ax6.text(0.1, 0.5, summary_text, fontsize=12, verticalalignment='center',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.suptitle(f'【{horizon}】模型综合评估报告', fontsize=16, y=1.02)

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✓ 图表已保存：{save_path}")
        plt.show()
        return fig, gs


# 便捷函数
def quick_plot_prediction(y_actual, y_pred, horizon='1D', save_path=None):
    """快速绘制预测对比图"""
    viz = ModelVisualizer()
    viz.plot_prediction_vs_actual(y_actual, y_pred, horizon, save_path=save_path)


def quick_plot_residuals(y_actual, y_pred, horizon='1D', save_path=None):
    """快速绘制残差分布图"""
    viz = ModelVisualizer()
    viz.plot_residual_distribution(y_actual, y_pred, horizon, save_path=save_path)


def quick_plot_scatter(y_actual, y_pred, horizon='1D', save_path=None):
    """快速绘制散点回归图"""
    viz = ModelVisualizer()
    viz.plot_scatter_regression(y_actual, y_pred, horizon, save_path=save_path)
