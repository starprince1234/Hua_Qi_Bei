"""
训练过程日志和可视化模块
记录模型训练过程中的关键数据和图表
"""

import pandas as pd
import numpy as np
import json
import os
import sys
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, mean_absolute_percentage_error

# 设置控制台编码（Windows）
if sys.platform == 'win32':
    sys.stdout = open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1, newline=None)

# 设置样式
sns.set_style("whitegrid")
sns.set_context("notebook", font_scale=1.0)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False


class TrainingLogger:
    """训练过程记录器"""
    
    def __init__(self, output_dir=None, project_root=None):
        """
        初始化记录器
        
        Args:
            output_dir: 输出目录（默认使用项目根目录的 outputs/training）
            project_root: 项目根目录（可选，如果提供则使用此路径）
        """
        if output_dir is None:
            if project_root is not None:
                # 使用传入的项目根目录
                output_dir = Path(project_root) / 'outputs' / 'training'
            else:
                # 使用 __file__ 计算（可能受 os.chdir 影响）
                import os
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'outputs', 'training')
        
        # 强制转换为绝对路径
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 存储训练过程中的数据
        self.data_split_info = {}
        self.optimization_history = []
        self.oof_results = {}
        self.training_history = {}
        self.test_evaluation = {}
        self.feature_importance_list = []
        
        # 开始时间
        self.start_time = datetime.now()
    
    # ============================================================
    # 1. 数据分割记录
    # ============================================================
    def log_data_split(self, X_train, X_val, X_test, y_train, y_val, y_test, 
                       date_col=None, df_original=None):
        """
        记录数据分割信息
        
        Args:
            X_train, X_val, X_test: 特征集
            y_train, y_val, y_test: 目标值
            date_col: 日期列名（如果有）
            df_original: 原始 DataFrame（用于获取日期范围）
        """
        info = {
            'timestamp': datetime.now().isoformat(),
            'sizes': {
                'train_size': len(X_train),
                'val_size': len(X_val),
                'test_size': len(X_test),
                'total_size': len(X_train) + len(X_val) + len(X_test)
            },
            'ratios': {
                'train_ratio': round(len(X_train) / (len(X_train) + len(X_val) + len(X_test)), 4),
                'val_ratio': round(len(X_val) / (len(X_train) + len(X_val) + len(X_test)), 4),
                'test_ratio': round(len(X_test) / (len(X_train) + len(X_val) + len(X_test)), 4)
            },
            'statistics': {
                'y_train': {
                    'mean': round(float(y_train.mean()), 6),
                    'std': round(float(y_train.std()), 6),
                    'min': round(float(y_train.min()), 6),
                    'max': round(float(y_train.max()), 6)
                },
                'y_val': {
                    'mean': round(float(y_val.mean()), 6),
                    'std': round(float(y_val.std()), 6),
                    'min': round(float(y_val.min()), 6),
                    'max': round(float(y_val.max()), 6)
                },
                'y_test': {
                    'mean': round(float(y_test.mean()), 6),
                    'std': round(float(y_test.std()), 6),
                    'min': round(float(y_test.min()), 6),
                    'max': round(float(y_test.max()), 6)
                }
            },
            'feature_count': X_train.shape[1]
        }
        
        # 如果有日期信息
        if date_col and df_original is not None and date_col in df_original.columns:
            n_train, n_val = len(X_train), len(X_val)
            info['date_ranges'] = {
                'train': [str(df_original[date_col].iloc[0]), str(df_original[date_col].iloc[n_train-1])],
                'val': [str(df_original[date_col].iloc[n_train]), str(df_original[date_col].iloc[n_train+n_val-1])],
                'test': [str(df_original[date_col].iloc[n_train+n_val]), str(df_original[date_col].iloc[-1])]
            }
        
        self.data_split_info = info
        
        # 绘制分割图
        self._plot_data_split(info)
        
        print(f"✓ 数据分割信息已记录")
        return info
    
    def _plot_data_split(self, info):
        """绘制数据分割可视化"""
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 左图：样本数量饼图
        sizes = [info['sizes']['train_size'], info['sizes']['val_size'], info['sizes']['test_size']]
        labels = [f"训练集\n{sizes[0]} ({info['ratios']['train_ratio']*100:.1f}%)",
                  f"验证集\n{sizes[1]} ({info['ratios']['val_ratio']*100:.1f}%)",
                  f"测试集\n{sizes[2]} ({info['ratios']['test_ratio']*100:.1f}%)"]
        colors = ['#2E86AB', '#A23B72', '#F18F01']
        
        axes[0].pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        axes[0].set_title('训练/验证/测试集 样本分布', fontsize=14)
        
        # 右图：目标变量分布
        ax = axes[1]
        ax.hist(info['statistics']['y_train']['mean'], bins=20, alpha=0.7, label='训练集', color='#2E86AB')
        ax.axvline(info['statistics']['y_train']['mean'], color='#2E86AB', linestyle='--', linewidth=2)
        ax.axvline(info['statistics']['y_val']['mean'], color='#A23B72', linestyle='--', linewidth=2)
        ax.axvline(info['statistics']['y_test']['mean'], color='#F18F01', linestyle='--', linewidth=2)
        ax.axvline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax.set_xlabel('目标变量均值')
        ax.set_title('各数据集目标变量均值对比', fontsize=14)
        ax.legend(['训练集均值', '验证集均值', '测试集均值', '零点'])
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        save_path = self.output_dir / '01_data_split.png'
        plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  [OK] 图表已保存：{save_path}")
    
    # ============================================================
    # 2. 贝叶斯优化记录
    # ============================================================
    def log_optimization_iteration(self, iteration, r2_score, params):
        """
        记录单次优化迭代
        
        Args:
            iteration: 迭代次数
            r2_score: R2分数
            params: 参数字典
        """
        # 只保留数值参数，排除嵌套字典
        record = {
            'iteration': iteration,
            'r2_score': round(float(r2_score), 6)
        }
        # 只添加数值类型的参数
        for k, v in params.items():
            if isinstance(v, (int, float)) and k not in ['monotone_constraints', 'n_estimators', 'early_stopping_rounds', 'random_state']:
                record[k] = round(float(v), 6)
        
        self.optimization_history.append(record)
        return record
    
    def finalize_optimization(self, best_params, best_score):
        """
        完成优化并保存结果
        
        Args:
            best_params: 最优参数
            best_score: 最优分数
        """
        # 绘制收敛曲线
        self._plot_optimization_convergence()
        
        # 保存优化历史
        history_df = pd.DataFrame(self.optimization_history)
        history_df.to_csv(self.output_dir / 'bayesian_optimization_history.csv', index=False, encoding='utf-8-sig')
        
        print(f"✓ 贝叶斯优化记录已保存")
        return {
            'best_params': best_params,
            'best_score': round(float(best_score), 6),
            'total_iterations': len(self.optimization_history)
        }
    
    def _plot_optimization_convergence(self):
        """绘制优化收敛曲线"""
        if not self.optimization_history:
            return
        
        df = pd.DataFrame(self.optimization_history)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))
        
        # 左图：收敛曲线
        ax = axes[0]
        ax.plot(df['iteration'], df['r2_score'], 'o-', color='#2E86AB', linewidth=2, markersize=6)
        ax.axhline(df['r2_score'].max(), color='#A23B72', linestyle='--', linewidth=2, alpha=0.7)
        ax.set_xlabel('迭代次数', fontsize=12)
        ax.set_ylabel('R2 分数', fontsize=12)
        ax.set_title('贝叶斯优化收敛曲线', fontsize=14)
        ax.grid(True, alpha=0.3)
        
        # 标注最优点
        best_idx = df['r2_score'].idxmax()
        ax.scatter([df.loc[best_idx, 'iteration']], [df.loc[best_idx, 'r2_score']], 
                  color='#F18F01', s=150, zorder=5, marker='*')
        ax.annotate(f'最优：{df.loc[best_idx, "r2_score"]:.4f}', 
                   xy=(df.loc[best_idx, 'iteration'], df.loc[best_idx, 'r2_score']),
                   xytext=(10, 10), textcoords='offset points', fontsize=10,
                   bbox=dict(boxstyle='round,pad=0.5', fc='#F18F01', alpha=0.7))
        
        # 右图：参数变化
        ax = axes[1]
        param_cols = [c for c in df.columns if c not in ['iteration', 'r2_score']]
        colors = plt.cm.Set2(np.linspace(0, 1, len(param_cols)))
        
        for i, col in enumerate(param_cols):
            ax.plot(df['iteration'], df[col], 'o-', label=col, color=colors[i], linewidth=1.5, markersize=4)
        
        ax.set_xlabel('迭代次数', fontsize=12)
        ax.set_ylabel('参数值', fontsize=12)
        ax.set_title('参数变化趋势', fontsize=14)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        save_path = self.output_dir / '02_bayesian_convergence.png'
        plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 图表已保存：{save_path}")
    
    # ============================================================
    # 3. OOF 交叉验证记录
    # ============================================================
    def log_oof_results(self, oof_xgb, oof_ridge, y_actual, fold_metrics=None):
        """
        记录 OOF 交叉验证结果
        
        Args:
            oof_xgb: XGBoost 的 OOF 预测
            oof_ridge: Ridge 的 OOF 预测
            y_actual: 实际值
            fold_metrics: 各折的指标列表
        """
        # 计算 OOF 指标
        oof_ensemble = (oof_xgb + oof_ridge) / 2
        
        results = {
            'oof_xgb_r2': round(float(r2_score(y_actual, oof_xgb)), 6),
            'oof_xgb_rmse': round(float(np.sqrt(mean_squared_error(y_actual, oof_xgb))), 6),
            'oof_ridge_r2': round(float(r2_score(y_actual, oof_ridge)), 6),
            'oof_ridge_rmse': round(float(np.sqrt(mean_squared_error(y_actual, oof_ridge))), 6),
            'oof_ensemble_r2': round(float(r2_score(y_actual, oof_ensemble)), 6),
            'oof_ensemble_rmse': round(float(np.sqrt(mean_squared_error(y_actual, oof_ensemble))), 6),
            'fold_metrics': fold_metrics or []
        }
        
        self.oof_results = results
        
        # 绘制 OOF 对比图
        self._plot_oof_comparison(oof_xgb, oof_ridge, oof_ensemble, y_actual)
        
        print(f"✓ OOF 交叉验证结果已记录")
        return results
    
    def _plot_oof_comparison(self, oof_xgb, oof_ridge, oof_ensemble, y_actual):
        """绘制 OOF 预测对比图"""
        # 计算 R2
        xgb_r2 = r2_score(y_actual, oof_xgb)
        ridge_r2 = r2_score(y_actual, oof_ridge)
        
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # 左图：OOF 预测 vs 实际值（折线图）
        ax = axes[0]
        n = len(y_actual)
        x = range(n)
        ax.plot(x, y_actual, label='实际值', color='#2E86AB', linewidth=1.5, alpha=0.8)
        ax.plot(x, oof_xgb, label='XGBoost OOF', color='#A23B72', linewidth=1.5, alpha=0.7, linestyle='--')
        ax.plot(x, oof_ridge, label='Ridge OOF', color='#F18F01', linewidth=1.5, alpha=0.7, linestyle='-.')
        ax.set_xlabel('样本索引', fontsize=12)
        ax.set_ylabel('涨跌幅 (%)', fontsize=12)
        ax.set_title('OOF 预测 vs 实际值', fontsize=14)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)

        # 右图：OOF 散点图
        ax = axes[1]
        ax.scatter(y_actual, oof_xgb, alpha=0.5, label=f'XGBoost (R2={xgb_r2:.4f})', color='#A23B72')
        ax.scatter(y_actual, oof_ridge, alpha=0.5, label=f'Ridge (R2={ridge_r2:.4f})', color='#F18F01')
        ax.plot([y_actual.min(), y_actual.max()], [y_actual.min(), y_actual.max()], 'k--', linewidth=2, alpha=0.7)
        ax.set_xlabel('实际值', fontsize=12)
        ax.set_ylabel('OOF 预测值', fontsize=12)
        ax.set_title('OOF 预测散点图', fontsize=14)
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        save_path = self.output_dir / '03_oof_comparison.png'
        plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 图表已保存：{save_path}")
    
    # ============================================================
    # 4. 特征重要性记录
    # ============================================================
    def log_feature_importance(self, importance_df, horizon, top_n=15):
        """
        记录特征重要性
        
        Args:
            importance_df: 特征重要性 DataFrame
            horizon: 周期（如 '7D'）
            top_n: 显示前 N 个特征
        """
        self.feature_importance_list.append({
            'horizon': horizon,
            'importance': importance_df.head(top_n)
        })
        
        # 绘制特征重要性图
        self._plot_feature_importance(importance_df, horizon, top_n)
        
        print(f"✓ 特征重要性已记录 ({horizon})")
    
    def _plot_feature_importance(self, importance_df, horizon, top_n=15):
        """绘制特征重要性图"""
        top_df = importance_df.head(top_n)
        
        fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.4)))
        
        # 翻转排序（从上到下递减）
        top_df = top_df.iloc[::-1]
        
        colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(top_df)))
        bars = ax.barh(range(len(top_df)), top_df['importance'].values, color=colors)
        
        ax.set_yticks(range(len(top_df)))
        ax.set_yticklabels(top_df['feature'].values, fontsize=10)
        ax.set_xlabel('重要性', fontsize=12)
        ax.set_title(f'【{horizon}】特征重要性 TOP {top_n}', fontsize=14)
        ax.grid(True, alpha=0.3, axis='x')
        
        # 标注数值
        for i, (idx, row) in enumerate(top_df.iterrows()):
            ax.text(row['importance'] + 0.001, i, f'{row["importance"]:.4f}', 
                   va='center', fontsize=9, color='#333')
        
        plt.tight_layout()
        save_path = self.output_dir / f'04_feature_importance_{horizon}.png'
        plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 图表已保存：{save_path}")
    
    # ============================================================
    # 5. 测试集评估记录
    # ============================================================
    def log_test_evaluation(self, metrics_dict, y_actual, predictions_dict, horizon):
        """
        记录测试集评估结果
        
        Args:
            metrics_dict: 指标字典
            y_actual: 实际值
            predictions_dict: 预测值字典 {model_name: predictions}
            horizon: 周期
        """
        # 计算残差
        residuals = {}
        for model_name, preds in predictions_dict.items():
            residuals[model_name] = y_actual - preds
        
        self.test_evaluation[horizon] = {
            'metrics': metrics_dict,
            'predictions': predictions_dict,
            'residuals': residuals
        }
        
        # 绘制评估图
        self._plot_test_evaluation(metrics_dict, y_actual, predictions_dict, horizon)
        
        print(f"✓ 测试集评估结果已记录 ({horizon})")
    
    def _plot_test_evaluation(self, metrics_dict, y_actual, predictions_dict, horizon):
        """绘制测试集评估图"""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        
        # 图 1：多模型指标对比
        ax = axes[0, 0]
        models = list(metrics_dict.keys())
        metrics_names = ['R2', 'RMSE', 'MAE', 'MAPE(%)']
        x = np.arange(len(models))
        width = 0.2
        
        colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
        for i, metric in enumerate(metrics_names):
            values = [metrics_dict[m].get(metric, 0) for m in models]
            ax.bar(x + i * width, values, width, label=metric, color=colors[i])
        
        ax.set_xlabel('模型', fontsize=12)
        ax.set_ylabel('分数', fontsize=12)
        ax.set_title(f'【{horizon}】多模型指标对比', fontsize=14)
        ax.set_xticks(x + width * 1.5)
        ax.set_xticklabels(models, fontsize=10)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3, axis='y')
        
        # 图 2：预测 vs 实际（折线图）
        ax = axes[0, 1]
        n = len(y_actual)
        x = range(n)
        ax.plot(x, y_actual, label='实际值', color='#2E86AB', linewidth=2, alpha=0.8)
        
        colors = ['#A23B72', '#F18F01', '#C73E1D']
        for i, (model_name, preds) in enumerate(predictions_dict.items()):
            ax.plot(x, preds, label=model_name, color=colors[i % len(colors)], 
                   linewidth=1.5, alpha=0.7, linestyle='--')
        
        ax.set_xlabel('样本索引', fontsize=12)
        ax.set_ylabel('涨跌幅 (%)', fontsize=12)
        ax.set_title(f'【{horizon}】预测 vs 实际', fontsize=14)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # 图 3：预测 vs 实际（散点图）
        ax = axes[1, 0]
        colors = ['#A23B72', '#F18F01', '#C73E1D']
        for i, (model_name, preds) in enumerate(predictions_dict.items()):
            r2 = metrics_dict[model_name].get('R2', 0)
            ax.scatter(y_actual, preds, alpha=0.5, label=f'{model_name} (R2={r2:.4f})', 
                      color=colors[i % len(colors)], s=30)
        
        ax.plot([y_actual.min(), y_actual.max()], [y_actual.min(), y_actual.max()], 
               'k--', linewidth=2, alpha=0.7)
        ax.set_xlabel('实际值', fontsize=12)
        ax.set_ylabel('预测值', fontsize=12)
        ax.set_title(f'【{horizon}】预测散点图', fontsize=14)
        ax.legend(fontsize=9)
        ax.grid(True, alpha=0.3)
        
        # 图 4：残差分布
        ax = axes[1, 1]
        residuals_list = [y_actual - preds for preds in predictions_dict.values()]
        labels = list(predictions_dict.keys())
        ax.boxplot(residuals_list, tick_labels=labels, patch_artist=True,
                  boxprops=dict(facecolor='#2E86AB', alpha=0.7))
        ax.axhline(0, color='black', linestyle='-', linewidth=1, alpha=0.5)
        ax.set_ylabel('残差', fontsize=12)
        ax.set_title(f'【{horizon}】残差分布', fontsize=14)
        ax.grid(True, alpha=0.3, axis='y')
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        save_path = self.output_dir / f'05_test_evaluation_{horizon}.png'
        plt.savefig(str(save_path), dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  ✓ 图表已保存：{save_path}")
    
    # ============================================================
    # 6. 保存完整报告
    # ============================================================
    def save_report(self, filename='training_report.json'):
        """保存完整训练报告"""
        report = {
            'start_time': self.start_time.isoformat(),
            'end_time': datetime.now().isoformat(),
            'data_split': self.data_split_info,
            'bayesian_optimization': {
                'history': self.optimization_history,
            },
            'oof_results': self.oof_results,
            'feature_importance': [
                {'horizon': fi['horizon'], 'top_features': fi['importance'].to_dict('records')}
                for fi in self.feature_importance_list
            ],
            'test_evaluation': {}  # 简化保存
        }
        
        # 简化 test_evaluation（只保存指标）
        for horizon, eval_data in self.test_evaluation.items():
            report['test_evaluation'][horizon] = eval_data['metrics']
        
        save_path = self.output_dir / filename
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ 完整训练报告已保存：{save_path}")
        print(f"{'='*60}")
        
        return report


# ============================================================
# 使用示例
# ============================================================
if __name__ == '__main__':
    import os
    # 示例：创建记录器（使用项目根目录的 outputs/training）
    # 使用绝对路径，不受当前工作目录影响
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logger = TrainingLogger(output_dir=os.path.join(project_root, 'outputs', 'training'))
    
    # 模拟数据
    np.random.seed(42)
    n = 1000
    X = pd.DataFrame(np.random.randn(n, 5), columns=[f'feature_{i}' for i in range(5)])
    y = pd.Series(np.random.randn(n))
    
    # 模拟数据分割
    X_train, X_val, X_test = X[:600], X[600:800], X[800:]
    y_train, y_val, y_test = y[:600], y[600:800], y[800:]
    
    logger.log_data_split(X_train, X_val, X_test, y_train, y_val, y_test)
    
    # 模拟优化过程
    for i in range(10):
        r2 = 0.5 + np.random.rand() * 0.4
        params = {'max_depth': np.random.randint(3, 7), 'learning_rate': np.random.rand() * 0.1}
        logger.log_optimization_iteration(i+1, r2, params)
    
    logger.finalize_optimization(
        best_params={'max_depth': 5, 'learning_rate': 0.05},
        best_score=0.85
    )
    
    # 模拟 OOF 结果
    oof_xgb = y.values + np.random.randn(len(y)) * 0.5
    oof_ridge = y.values + np.random.randn(len(y)) * 0.6
    logger.log_oof_results(oof_xgb, oof_ridge, y.values)
    
    # 模拟特征重要性
    importance_df = pd.DataFrame({
        'feature': [f'feature_{i}' for i in range(5)],
        'importance': np.random.rand(5)
    }).sort_values('importance', ascending=False)
    logger.log_feature_importance(importance_df, horizon='7D')
    
    # 模拟测试评估
    metrics = {
        'XGBoost': {'R2': 0.78, 'RMSE': 1.23, 'MAE': 0.89, 'MAPE(%)': 12.34},
        'Ridge': {'R2': 0.65, 'RMSE': 1.45, 'MAE': 1.02, 'MAPE(%)': 15.67},
        'Stacking': {'R2': 0.82, 'RMSE': 1.12, 'MAE': 0.81, 'MAPE(%)': 10.89}
    }
    predictions = {
        'XGBoost': y_test.values + np.random.randn(len(y_test)) * 0.5,
        'Ridge': y_test.values + np.random.randn(len(y_test)) * 0.6,
        'Stacking': y_test.values + np.random.randn(len(y_test)) * 0.4
    }
    logger.log_test_evaluation(metrics, y_test.values, predictions, horizon='7D')
    
    # 保存报告
    logger.save_report()
