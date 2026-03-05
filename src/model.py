import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.linear_model import RidgeCV, LinearRegression
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error, mean_absolute_percentage_error
import joblib
import warnings
warnings.filterwarnings('ignore')

# 数据文件映射
DATA_FILES = {
    '1D': '../data/processed/油价预测1日波动率因子表.xlsx',
    '3D': '../data/processed/油价预测3日波动率因子表.xlsx',
    '7D': '../data/processed/油价预测7日波动率因子表.xlsx',
    '14D': '../data/processed/油价预测14日波动率因子表.xlsx',
    '30D': '../data/processed/油价预测30日波动率因子表.xlsx'
}

# 目标变量列名
TARGET_COLS = {
    '1D': 'Brent_close_1日涨跌幅(%)',
    '3D': 'Brent_close_3日涨跌幅(%)',
    '7D': 'Brent_close_7日涨跌幅(%)',
    '14D': 'Brent_close_14日涨跌幅(%)',
    '30D': 'Brent_close_30日涨跌幅(%)'
}


class BaseModels:
    """Layer 1基模型封装"""

    def __init__(self, monotone_constraints=None, xgb_params=None):
        self.monotone_constraints = monotone_constraints or {}
        self.xgb_params = xgb_params
        self.xgb_model = None
        self.ridge_model = None

    def _convert_constraints_to_indices(self, X, constraints_dict):
        """将列名约束字典转换为列位置索引"""
        if not constraints_dict:
            return {}
        
        col_to_idx = {col: idx for idx, col in enumerate(X.columns)}
        indices_constraints = {}
        for col_name, constraint_val in constraints_dict.items():
            if col_name in col_to_idx:
                indices_constraints[col_to_idx[col_name]] = constraint_val
        return indices_constraints

    def train_xgb(self, X, y, eval_set=None):
        """训练XGBoost模型"""
        # 将列名约束转换为列位置索引
        constraints_indices = self._convert_constraints_to_indices(X, self.monotone_constraints)
        
        # 如果有优化参数，使用它们；否则使用默认参数
        if self.xgb_params:
            params = self.xgb_params.copy()
            params['monotone_constraints'] = constraints_indices if constraints_indices else None
        else:
            params = {
                'objective': 'reg:squarederror',
                'max_depth': 4,
                'learning_rate': 0.03,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'n_estimators': 1000,
                'early_stopping_rounds': 50,
                'random_state': 42,
                'monotone_constraints': constraints_indices if constraints_indices else None
            }

    #没有验证集时，删除早停参数
        if eval_set is None and 'early_stopping_rounds' in params:
            del params['early_stopping_rounds']

        self.xgb_model = xgb.XGBRegressor(**params)
        self.xgb_model.fit(
            X, y,
            eval_set=eval_set,
            verbose=False
        )
        return self.xgb_model

    def train_ridge(self, X, y):
        """训练Ridge回归模型"""
        self.ridge_model = RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0])
        self.ridge_model.fit(X, y)
        return self.ridge_model

    def predict(self, X):
        """基模型预测"""
        xgb_pred = self.xgb_model.predict(X)
        ridge_pred = self.ridge_model.predict(X)
        return xgb_pred, ridge_pred


class StackingModel:
    """Stacking集成模型"""

    def __init__(self, horizon='1D', monotone_constraints=None, xgb_params=None):
        self.horizon = horizon
        self.monotone_constraints = monotone_constraints or {}
        self.xgb_params = xgb_params
        self.base_models = None
        self.meta_model = None
        self.quantile_models = {}

    def create_oof_predictions(self, X, y, n_splits=5):
        """生成OOF预测作为元特征 - 保持时序性"""
        # ✅ 所有周期都使用 TimeSeriesSplit，保持时序依赖关系
        # 原理：只用历史数据预测未来，避免时间泄露
        kf = TimeSeriesSplit(n_splits=n_splits)

        oof_xgb = np.zeros(len(X))
        oof_ridge = np.zeros(len(X))

        for fold_idx, (train_idx, val_idx) in enumerate(kf.split(X)):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

            # 训练基模型（传递单调约束 和 优化参数）
            # TimeSeriesSplit 保证了：train_idx < val_idx，遵守时序性
            base_models = BaseModels(
                monotone_constraints=self.monotone_constraints,
                xgb_params=self.xgb_params
            )
            base_models.train_xgb(X_train, y_train, eval_set=[(X_val, y_val)])
            base_models.train_ridge(X_train, y_train)

            # 验证集预测
            xgb_pred, ridge_pred = base_models.predict(X_val)
            oof_xgb[val_idx] = xgb_pred
            oof_ridge[val_idx] = ridge_pred

        return oof_xgb, oof_ridge

    def train(self, X, y):
        """训练完整Stacking模型"""
        # 说明：该方法在完整数据上进行训练
        # 在生产环境中，应该使用 train_all_horizons_with_optimization() 的流程
        # 该流程会：先用训练集优化参数，再用所有数据训练最终模型，最后在测试集评估
        
        # 1. 生成OOF预测 (使用 TimeSeriesSplit 保持时序性)
        oof_xgb, oof_ridge = self.create_oof_predictions(X, y)

        # 2. 创建元特征
        meta_features = np.column_stack([oof_xgb, oof_ridge])

        # 3. 训练元模型
        self.meta_model = LinearRegression(fit_intercept=False)
        self.meta_model.fit(meta_features, y)

        # 4. 最终基模型训练（全量数据，应用相同的单调约束和优化参数）
        self.base_models = BaseModels(
            monotone_constraints=self.monotone_constraints,
            xgb_params=self.xgb_params
        )
        self.base_models.train_xgb(X, y)
        self.base_models.train_ridge(X, y)

        return self

    def train_quantile_models(self, X, y):
        """训练分位数回归模型"""
        quantiles = [0.05, 0.50, 0.95]
        
        # 转换列名约束为列位置索引
        col_to_idx = {col: idx for idx, col in enumerate(X.columns)}
        constraints_indices = {}
        for col_name, constraint_val in self.monotone_constraints.items():
            if col_name in col_to_idx:
                constraints_indices[col_to_idx[col_name]] = constraint_val

        for q in quantiles:
            params = {
                'objective': 'reg:quantileerror',
                'quantile_alpha': q,
                'max_depth': 4,
                'learning_rate': 0.03,
                'subsample': 0.8,
                'n_estimators': 500,
                'random_state': 42,
                'monotone_constraints': constraints_indices if constraints_indices else None
            }

            model = xgb.XGBRegressor(**params)
            model.fit(X, y, verbose=False)
            self.quantile_models[q] = model

        return self

    # ============ 功能1: 特征重要性 ============
    def get_feature_importance(self, top_n=15):
        """获取特征重要性排名 (TOP N)"""
        if self.base_models is None or self.base_models.xgb_model is None:
            return None
        
        importance_df = pd.DataFrame({
            'feature': self.base_models.xgb_model.feature_names_in_,
            'importance': self.base_models.xgb_model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        return importance_df.head(top_n)

    # ============ 功能2: 模型评估指标 ============
    def evaluate_on_validation_set(self, X_val, y_val):
        """计算验证集评估指标: R2, RMSE, MAE, MAPE"""
        # 基模型预测
        xgb_pred, ridge_pred = self.base_models.predict(X_val)
        
        # 集成模型预测
        meta_features = np.column_stack([xgb_pred, ridge_pred])
        ensemble_pred = self.meta_model.predict(meta_features)
        
        # 计算评估指标
        metrics = {}
        
        # XGBoost性能
        metrics['XGBoost'] = {
            'R²': round(r2_score(y_val, xgb_pred), 4),
            'RMSE': round(np.sqrt(mean_squared_error(y_val, xgb_pred)), 4),
            'MAE': round(mean_absolute_error(y_val, xgb_pred), 4),
            'MAPE(%)': round(mean_absolute_percentage_error(np.abs(y_val) + 0.001, np.abs(xgb_pred) + 0.001) * 100, 2)
        }
        
        # Ridge性能
        metrics['Ridge'] = {
            'R²': round(r2_score(y_val, ridge_pred), 4),
            'RMSE': round(np.sqrt(mean_squared_error(y_val, ridge_pred)), 4),
            'MAE': round(mean_absolute_error(y_val, ridge_pred), 4),
            'MAPE(%)': round(mean_absolute_percentage_error(np.abs(y_val) + 0.001, np.abs(ridge_pred) + 0.001) * 100, 2)
        }
        
        # Stacking集成性能
        metrics['Stacking'] = {
            'R²': round(r2_score(y_val, ensemble_pred), 4),
            'RMSE': round(np.sqrt(mean_squared_error(y_val, ensemble_pred)), 4),
            'MAE': round(mean_absolute_error(y_val, ensemble_pred), 4),
            'MAPE(%)': round(mean_absolute_percentage_error(np.abs(y_val) + 0.001, np.abs(ensemble_pred) + 0.001) * 100, 2)
        }
        
        return metrics

    # ============ 功能3: 预测性能对比 ============
    def print_performance_comparison(self, X_val, y_val):
        """打印基模型vs集成模型的性能对比报告"""
        metrics = self.evaluate_on_validation_set(X_val, y_val)
        
        print("\n【预测性能对比】")
        print("="*70)
        print(f"{'模型':<15} {'R²':<10} {'RMSE':<12} {'MAE':<12} {'MAPE(%)':<10}")
        print("-"*70)
        
        for model_name, scores in metrics.items():
            print(f"{model_name:<15} {scores['R²']:<10} {scores['RMSE']:<12} {scores['MAE']:<12} {scores['MAPE(%)']:<10}")
        
        # 计算集成模型相对基模型的改进
        xgb_r2 = metrics['XGBoost']['R²']
        ensemble_r2 = metrics['Stacking']['R²']
        improvement = round((ensemble_r2 - xgb_r2) / (abs(xgb_r2) + 0.001) * 100, 2) if xgb_r2 != 0 else 0
        
        print("-"*70)
        print(f"✓ 集成模型相对XGBoost的R²改进: {improvement}%")
        print()

    # ============ 功能4: 模型配置总结 ============
    def get_model_metrics_summary(self):
        """获取模型元学习器系数和配置信息"""
        summary = {
            'horizon': self.horizon,
            'meta_model_coef': {
                'XGBoost_weight': round(float(self.meta_model.coef_[0]), 4) if len(self.meta_model.coef_) > 0 else 0,
                'Ridge_weight': round(float(self.meta_model.coef_[1]), 4) if len(self.meta_model.coef_) > 1 else 0,
                'intercept': round(float(self.meta_model.intercept_), 6)
            },
            'monotone_constraints': self.monotone_constraints if self.monotone_constraints else '无',
            'quantile_models': list(self.quantile_models.keys())
        }
        return summary

    def predict_with_risk(self, X, current_price):
        """带风险区间的预测"""
        # 1. 基模型预测
        xgb_pred, ridge_pred = self.base_models.predict(X)

        # 2. Stacking集成预测
        meta_features = np.column_stack([xgb_pred, ridge_pred])
        final_return = self.meta_model.predict(meta_features)[0]

        # 3. 分位数预测
        q05_return = self.quantile_models[0.05].predict(X)[0]
        q50_return = self.quantile_models[0.50].predict(X)[0]
        q95_return = self.quantile_models[0.95].predict(X)[0]

        # 4. 价格还原
        predicted_price = current_price * (1 + final_return)
        price_05 = current_price * (1 + q05_return)
        price_50 = current_price * (1 + q50_return)
        price_95 = current_price * (1 + q95_return)

        # 5. 分位数交叉修正
        if price_05 > price_50:
            price_05 = price_50 * 0.99
        if price_95 < price_50:
            price_95 = price_50 * 1.01

        return {
            'horizon': self.horizon,
            'current_price': current_price,
            'predicted_return': round(final_return, 6),
            'predicted_price': round(predicted_price, 4),
            'risk_interval': [round(price_05, 4), round(price_95, 4)]
        }


class OilPricePredictor:
    """主控制器类"""

    def __init__(self):
        self.models = {}

    def train_all_horizons_with_optimization(self, bayesian_n_iter=20,
                                         train_ratio=0.6,
                                         val_ratio=0.2,
                                         test_ratio=0.2,
                                         save_training_logs=True):
        """
        使用贝叶斯优化训练所有周期的模型

        工作流程：
        1. 加载数据 → 特征提取
        2. 数据分割：60% 训练 + 20% 验证 + 20% 测试
        3. 贝叶斯优化：搜索最优参数
        4. 模型训练：用优化参数在完整数据上训练
        5. 性能评估：在测试集上评估

        Args:
            save_training_logs: 是否保存训练日志和可视化
        """
        from param_optimizer import DataSplitter, BayesianOptimizer

        for horizon, file_path in DATA_FILES.items():
            print(f"\n{'='*80}")
            print(f"【{horizon} 周期 - 完整训练流程】")
            print(f"{'='*80}")

            # 初始化训练日志记录器（为每个周期创建独立的文件夹）
            logger = None
            if save_training_logs:
                from training_logger import TrainingLogger
                import os
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                period_output_dir = os.path.join(project_root, 'outputs', 'training', horizon)
                logger = TrainingLogger(output_dir=period_output_dir)
            
            # 第1步：加载和清洗数据
            try:
                df = pd.read_excel(file_path)
            except FileNotFoundError:
                print(f"✗ 文件不存在: {file_path}")
                continue
            
            target_col = TARGET_COLS[horizon]
            if target_col not in df.columns:
                print(f"✗ 目标列不存在: {target_col}")
                continue
            
            y = df[target_col]
            cols_to_drop = [target_col]
            if '日期' in df.columns:
                cols_to_drop.append('日期')
            X = df.drop(columns=cols_to_drop)
            
            # 过滤非数值类型的列（XGBoost 要求）
            numeric_cols = X.select_dtypes(include=['int', 'float', 'bool']).columns
            non_numeric_cols = set(X.columns) - set(numeric_cols)
            if non_numeric_cols:
                print(f"  移除非数值列：{list(non_numeric_cols)}")
                X = X[numeric_cols]

            print(f"\n✓ 数据加载完成")
            print(f"  总样本数: {len(X)}, 特征数: {X.shape[1]}")
            
            # 第2步：数据分割
            print(f"\n✓ 数据分割 ({train_ratio*100:.0f}% 训练 | "
                f"{val_ratio*100:.0f}% 验证 | {test_ratio*100:.0f}% 测试)")
            
            split_data = DataSplitter.split_data(
                X, y, 
                train_ratio=train_ratio,
                val_ratio=val_ratio,
                test_ratio=test_ratio
            )
            
            X_train = split_data['X_train']
            y_train = split_data['y_train']
            X_val = split_data['X_val']
            y_val = split_data['y_val']
            X_test = split_data['X_test']
            y_test = split_data['y_test']
            
            print(f"  训练集: {len(X_train)} | 验证集: {len(X_val)} | 测试集: {len(X_test)}")

            
            # 记录数据分割日志
            if logger:
                date_col = '日期' if '日期' in df.columns else None
                logger.log_data_split(
                    X_train, X_val, X_test, y_train, y_val, y_test,
                    date_col=date_col, df_original=df
                )
            
            # 检查单调性约束
            monotone_constraints = {}
            inventory_cols = [col for col in X.columns if '库存' in col or 'Inventory' in col]
            if inventory_cols:
                for col in inventory_cols:
                    monotone_constraints[col] = -1
            
            # 第3步：贝叶斯参数优化
            print(f"\n第3步：贝叶斯参数优化...")
            optimizer = BayesianOptimizer(
                X_train, y_train, X_val, y_val,
                monotone_constraints=monotone_constraints
            )
            best_params = optimizer.optimize(n_iter=bayesian_n_iter)

            # 记录优化日志
            if logger:
                for record in optimizer.optimization_history:
                    logger.log_optimization_iteration(
                        record['iteration'],
                        record['r2_score'],  # 修复：字段名是 r2_score 不是 target
                        record['params']  # 传递参数字典
                    )
                logger.finalize_optimization(best_params, optimizer.best_score)
            
            # 第4步：用最优参数训练模型
            print(f"\n第4步：使用优化参数训练最终模型...")
            model = StackingModel(
                horizon=horizon,
                monotone_constraints=monotone_constraints,
                xgb_params=best_params
            )
            
            # ✅ 改进：用训练集+验证集一起训练最终模型，充分利用数据
            # 验证集原本只用于贝叶斯优化，现在用于提升最终模型
            X_full_train = pd.concat([X_train, X_val], ignore_index=True)
            y_full_train = pd.concat([y_train, y_val], ignore_index=True)
            
            model.train(X_full_train, y_full_train)
            model.train_quantile_models(X_full_train, y_full_train)
            
            # 第5步：在测试集上评估
            print(f"\n第5步：在测试集上最终评估...")
            test_metrics = model.evaluate_on_validation_set(X_test, y_test)
            model.print_performance_comparison(X_test, y_test)
            
            self.models[horizon] = {
                'model': model,
                'best_params': best_params,
                'test_metrics': test_metrics,
                'split_indices': {
                    'train_size': len(X_train),
                    'val_size': len(X_val),
                    'test_size': len(X_test)
                }
            }
            
            print(f"\n✓ {horizon} 模型训练完成\n")


            # Save training report
            if logger:
                logger.save_report()

    def save_models(self, filename='OilPrice_Full_Suite.pkl'):
        """保存所有模型到项目根目录"""
        import os
        # 获取 model.py 所在目录的父目录（项目根目录，与 src 同级）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_path = os.path.join(project_root, filename)
        joblib.dump(self.models, save_path)
        print(f"✓ 模型已保存到 {save_path}")
        return save_path

    def load_models(self, filename='OilPrice_Full_Suite.pkl'):
        """加载模型（从项目根目录加载）"""
        import os
        # 获取项目根目录，确保路径一致性
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_path = os.path.join(project_root, filename)
        self.models = joblib.load(load_path)
        print(f"✓ 模型已加载：{load_path}")
        return self
    


def example_usage():
    """使用示例"""
    # 训练模型
    predictor = OilPricePredictor()
    # 使用贝叶斯优化训练
    predictor.train_all_horizons_with_optimization(
        bayesian_n_iter=20,      # 贝叶斯优化迭代20次
        train_ratio=0.6,          # 60% 训练集
        val_ratio=0.2,            # 20% 验证集
        test_ratio=0.2            # 20% 测试集
    )
    predictor.save_models()
    # 加载模型并进行预测
    predictor.load_models()


if __name__ == '__main__':
    example_usage()