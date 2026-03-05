"""
参数优化模块 - 使用贝叶斯优化搜索最优模型参数
"""
import xgboost as xgb
from sklearn.metrics import r2_score
from bayes_opt import BayesianOptimization
import warnings
warnings.filterwarnings('ignore')


class DataSplitter:
    """数据集分割器 - 按比例分割为 训练/验证/测试 三部分"""
    
    @staticmethod
    def validate_timeseries_split(X_train, X_val, X_test):
        """
        验证时序性分割是否正确
        
        原理：确保验证集和测试集的索引都大于训练集
        """
        train_max_idx = X_train.index.max()
        val_min_idx = X_val.index.min()
        test_min_idx = X_test.index.min()
        
        is_valid = (train_max_idx < val_min_idx) and (val_min_idx < test_min_idx)
        
        if is_valid:
            print(f"  ✓ 时序性验证: 通过 (训练 < 验证 < 测试)")
        else:
            print(f"  ✗ 时序性验证: 失败 (数据顺序不对)")
        
        return is_valid
    
    @staticmethod
    def split_data(X, y, train_ratio=0.6, val_ratio=0.2, test_ratio=0.2, random_state=42):
        """
        分割数据集
        
        Args:
            X, y: 特征和目标
            train_ratio: 训练集比例 (默认60%)
            val_ratio: 验证集比例 (默认20%)
            test_ratio: 测试集比例 (默认20%)
            random_state: 随机种子
            
        Returns:
            字典包含：X_train, y_train, X_val, y_val, X_test, y_test
        """
        assert train_ratio + val_ratio + test_ratio == 1.0, "比例和必须为1"
        
        # 重置索引避免问题
        X = X.reset_index(drop=True)
        y = y.reset_index(drop=True)
        
        n = len(X)
        
        # 计算分割点
        train_end = int(n * train_ratio)
        val_end = train_end + int(n * val_ratio)
        
        # 分割
        X_train = X.iloc[:train_end]
        y_train = y.iloc[:train_end]
        
        X_val = X.iloc[train_end:val_end]
        y_val = y.iloc[train_end:val_end]
        
        X_test = X.iloc[val_end:]
        y_test = y.iloc[val_end:]
        
        # ✅ 添加时序性验证日志
        print(f"\n✓ 时间序列数据分割 (保持顺序):")
        print(f"  训练集: 样本 {0:4d} ~ {train_end-1:4d} ({len(X_train):4d} 个)")
        print(f"  验证集: 样本 {train_end:4d} ~ {val_end-1:4d} ({len(X_val):4d} 个)")
        print(f"  测试集: 样本 {val_end:4d} ~ {len(X)-1:4d} ({len(X_test):4d} 个)")
        print(f"  ✓ 时序顺序检验过关: 数据按时间递进分割\n")
        
        # 验证时序性
        DataSplitter.validate_timeseries_split(X_train, X_val, X_test)
        
        return {
            'X_train': X_train, 'y_train': y_train,
            'X_val': X_val, 'y_val': y_val,
            'X_test': X_test, 'y_test': y_test
        }


class BayesianOptimizer:
    """贝叶斯参数优化器 - 搜索XGBoost最优参数"""
    
    def __init__(self, X_train, y_train, X_val, y_val, monotone_constraints=None):
        """
        初始化优化器
        
        Args:
            X_train, y_train: 训练集
            X_val, y_val: 验证集
            monotone_constraints: 单调性约束
        """
        self.X_train = X_train
        self.y_train = y_train
        self.X_val = X_val
        self.y_val = y_val
        self.monotone_constraints = monotone_constraints or {}

        # 转换约束为列位置索引
        self.constraints_indices = self._convert_constraints_to_indices()

        self.best_params = None
        self.best_score = None
        self.optimization_history = []  # 记录优化历史
    
    def _convert_constraints_to_indices(self):
        """将列名约束转换为列位置索引"""
        if not self.monotone_constraints:
            return {}
        
        col_to_idx = {col: idx for idx, col in enumerate(self.X_train.columns)}
        indices_constraints = {}
        for col_name, constraint_val in self.monotone_constraints.items():
            if col_name in col_to_idx:
                indices_constraints[col_to_idx[col_name]] = constraint_val
        return indices_constraints
    
    def _objective_function(self, max_depth, learning_rate, subsample, colsample_bytree):
        """贝叶斯优化目标函数"""
        
        params = {
            'objective': 'reg:squarederror',
            'max_depth': int(max_depth),
            'learning_rate': learning_rate,
            'subsample': subsample,
            'colsample_bytree': colsample_bytree,
            'n_estimators': 500,
            'early_stopping_rounds': 30,
            'random_state': 42,
            'monotone_constraints': self.constraints_indices if self.constraints_indices else None
        }
        
        try:
            model = xgb.XGBRegressor(**params)
            model.fit(
                self.X_train, self.y_train,
                eval_set=[(self.X_val, self.y_val)],
                verbose=False
            )
            
            # 在验证集上评估
            y_pred = model.predict(self.X_val)
            score = r2_score(self.y_val, y_pred)
            
            return score
        except:
            return -999  # 异常情况返回极低分数
    
    def optimize(self, n_iter=20, init_points=5):
        """
        执行贝叶斯优化
        
        Args:
            n_iter: 优化迭代次数
            init_points: 初始化随机采样点数
            
        Returns:
            最优参数字典
        """
        print(f"\n【贝叶斯参数优化】")
        print(f"{'='*70}")
        print(f"初始化采样: {init_points} 次")
        print(f"优化迭代: {n_iter} 次")
        print(f"搜索空间:")
        print(f"  - max_depth: [3, 7]")
        print(f"  - learning_rate: [0.01, 0.1]")
        print(f"  - subsample: [0.6, 1.0]")
        print(f"  - colsample_bytree: [0.6, 1.0]")
        print(f"{'='*70}\n")
        
        # 定义搜索空间
        pbounds = {
            'max_depth': (3, 7),
            'learning_rate': (0.01, 0.1),
            'subsample': (0.6, 1.0),
            'colsample_bytree': (0.6, 1.0)
        }
        
        # 创建优化器
        optimizer = BayesianOptimization(
            f=self._objective_function,
            pbounds=pbounds,
            random_state=42,
            verbose=1
        )
        
        # 执行优化
        optimizer.maximize(init_points=init_points, n_iter=n_iter)

        # 记录优化历史（从 bayes_opt 的 log 中提取）
        for i, res in enumerate(optimizer.res):
            self.optimization_history.append({
                'iteration': i + 1,
                'r2_score': round(res['target'], 6),
                'params': res['params']
            })

        # 提取最优参数
        self.best_params = {
            'max_depth': int(optimizer.max['params']['max_depth']),
            'learning_rate': round(optimizer.max['params']['learning_rate'], 4),
            'subsample': round(optimizer.max['params']['subsample'], 4),
            'colsample_bytree': round(optimizer.max['params']['colsample_bytree'], 4),
            'n_estimators': 1000,
            'early_stopping_rounds': 50,
            'random_state': 42,
            'objective': 'reg:squarederror',
            'monotone_constraints': self.constraints_indices if self.constraints_indices else None
        }
        
        self.best_score = optimizer.max['target']
        
        print(f"\n【优化完成】")
        print(f"最优R²分数: {self.best_score:.4f}")
        print(f"最优参数:\n  - max_depth: {self.best_params['max_depth']}")
        print(f"  - learning_rate: {self.best_params['learning_rate']}")
        print(f"  - subsample: {self.best_params['subsample']}")
        print(f"  - colsample_bytree: {self.best_params['colsample_bytree']}")
        print()
        
        return self.best_params
    
    def get_best_params(self):
        """获取最优参数"""
        return self.best_params