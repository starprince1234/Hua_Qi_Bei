"""
油价预测系统 - 回测框架
用于历史数据回测、性能评估
"""

import pandas as pd
import numpy as np
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
import joblib
import warnings
warnings.filterwarnings('ignore')

from model import StackingModel,BaseModels

class BacktestEngine:
    """回测引擎 - 用于历史数据验证模型性能"""

    def __init__(self, models_path='OilPrice_Full_Suite.pkl'):
        """
        初始化回测引擎
        
        Args:
            models_path: 模型文件路径
        """
        self.models = joblib.load(models_path)
        print(f"✓ 已加载模型: {models_path}")
        
    def walk_forward_backtest(self, df, target_col, horizon, train_size=0.7, test_size=0.2):
        """
        走向前回测 (Walk-Forward Backtest)
        - 模拟在线学习场景
        - 逐步扩展训练窗口，保留测试集
        
        Args:
            df: 包含特征和目标的DataFrame
            target_col: 目标列名
            horizon: 预测周期 ('1D', '3D', '7D', '14D', '30D')
            train_size: 初始训练集比例
            test_size: 每次测试集比例
            
        Returns:
            backtest_results: 回测结果DataFrame
        """
        print(f"\n【{horizon} 走向前回测】")
        print("="*80)
        
        # 特征提取
        X = df.drop(columns=[target_col] if target_col in df.columns else [])
        y = df[target_col]
        
        # 初始训练/测试划分
        n = len(X)
        train_end = int(n * train_size)
        
        predictions = []
        actuals = []
        timestamps = []
        
        # 走向前回测
        current_pos = train_end
        while current_pos + int(n * test_size) <= n:
            test_end = min(current_pos + int(n * test_size), n)
            
            X_test = X.iloc[current_pos:test_end]
            y_test = y.iloc[current_pos:test_end]
            
            # 使用已训练的模型预测
            model = self.models.get(horizon)
            if model is None:
                print(f"✗ 模型 {horizon} 不存在")
                return None
            
            # 逐样本预测
            for idx in range(len(X_test)):
                X_sample = X_test.iloc[idx:idx+1]
                y_sample = y_test.iloc[idx]
                
                # 基模型预测
                xgb_pred, ridge_pred = model.base_models.predict(X_sample)
                
                # Stacking预测
                meta_features = np.column_stack([xgb_pred, ridge_pred])
                pred = model.meta_model.predict(meta_features)[0]
                
                predictions.append(pred)
                actuals.append(y_sample)
                timestamps.append(current_pos + idx)
            
            current_pos = test_end
        
        # 生成回测结果
        results = pd.DataFrame({
            'timestamp': timestamps,
            'actual': actuals,
            'predicted': predictions,
            'error': np.array(actuals) - np.array(predictions),
            'abs_error': np.abs(np.array(actuals) - np.array(predictions))
        })
        
        return results
    
    def rolling_window_backtest(self, df, target_col, horizon, window_size=50, step=5):
        """
        滚动窗口回测
        - 使用固定大小的滚动窗口
        
        Args:
            df: 包含特征和目标的DataFrame
            target_col: 目标列名
            horizon: 预测周期
            window_size: 窗口大小
            step: 每次滚动步长
            
        Returns:
            backtest_results: 回测结果DataFrame
        """
        print(f"\n【{horizon} 滚动窗口回测 (窗口大小={window_size}, 步长={step})】")
        print("="*80)
        
        X = df.drop(columns=[target_col] if target_col in df.columns else [])
        y = df[target_col]
        
        predictions = []
        actuals = []
        timestamps = []
        
        model = self.models.get(horizon)
        if model is None:
            print(f"✗ 模型 {horizon} 不存在")
            return None
        
        # 滚动窗口
        for i in range(0, len(X) - window_size, step):
            test_start = i + window_size
            test_end = min(test_start + step, len(X))
            
            X_test = X.iloc[test_start:test_end]
            y_test = y.iloc[test_start:test_end]
            
            for idx in range(len(X_test)):
                X_sample = X_test.iloc[idx:idx+1]
                y_sample = y_test.iloc[idx]
                
                xgb_pred, ridge_pred = model.base_models.predict(X_sample)
                meta_features = np.column_stack([xgb_pred, ridge_pred])
                pred = model.meta_model.predict(meta_features)[0]
                
                predictions.append(pred)
                actuals.append(y_sample)
                timestamps.append(test_start + idx)
        
        results = pd.DataFrame({
            'timestamp': timestamps,
            'actual': actuals,
            'predicted': predictions,
            'error': np.array(actuals) - np.array(predictions),
            'abs_error': np.abs(np.array(actuals) - np.array(predictions))
        })
        
        return results
    
    def print_backtest_report(self, backtest_results, horizon):
        """打印回测报告"""
        if backtest_results is None or len(backtest_results) == 0:
            print("✗ 无回测结果")
            return
        
        actual = backtest_results['actual'].values
        predicted = backtest_results['predicted'].values
        
        r2 = r2_score(actual, predicted)
        rmse = np.sqrt(mean_squared_error(actual, predicted))
        mae = mean_absolute_error(actual, predicted)
        hit_rate = np.sum(np.sign(actual) == np.sign(predicted)) / len(actual) * 100
        
        print(f"\n【{horizon} 回测统计结果】")
        print("="*80)
        print(f"样本数: {len(backtest_results)}")
        print(f"R² Score: {r2:.4f}")
        print(f"RMSE: {rmse:.4f}")
        print(f"MAE: {mae:.4f}")
        print(f"方向准确率 (Hit Rate): {hit_rate:.2f}%")
        print(f"平均绝对误差: {backtest_results['abs_error'].mean():.4f}")
        print(f"最大误差: {backtest_results['abs_error'].max():.4f}")
        print("="*80)
        
        return {
            'r2': r2,
            'rmse': rmse,
            'mae': mae,
            'hit_rate': hit_rate
        }


# 使用示例
if __name__ == '__main__':
    # 初始化回测引擎
    backtest = BacktestEngine('OilPrice_Full_Suite.pkl')
    
    # 加载数据示例（需要替换为实际数据路径）
    # df = pd.read_excel('../data/processed/油价预测7日波动率因子表.xlsx')
    # 
    # # 走向前回测
    # results_wf = backtest.walk_forward_backtest(df, 'Brent_close_7日涨跌幅(%)', '7D')
    # backtest.print_backtest_report(results_wf, '7D (Walk-Forward)')
    # 
    # # 滚动窗口回测
    # results_rw = backtest.rolling_window_backtest(df, 'Brent_close_7日涨跌幅(%)', '7D')
    # backtest.print_backtest_report(results_rw, '7D (Rolling Window)')