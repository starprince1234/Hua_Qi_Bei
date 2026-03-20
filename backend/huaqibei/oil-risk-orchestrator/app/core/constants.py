"""
全局常量定义
"""

# 特征工程常量
FEATURE_NA_FILL_VALUE: float = 0.0

# 数据行数限制
MIN_REQUIRED_ROWS: int = 30
MAX_UPLOAD_ROWS: int = 5000

# 预测步数支持列表
SUPPORTED_HORIZONS: list[int] = [1, 3, 7, 14, 30]

# 风险等级阈值
RISK_LOW_THRESHOLD: float = 0.02
RISK_HIGH_THRESHOLD: float = 0.05
RISK_EXTREME_THRESHOLD: float = 0.10

# API 路由前缀
API_V1_PREFIX: str = "/api/v1"

# 文件上传限制
MAX_FILE_SIZE_MB: int = 10
ALLOWED_EXTENSIONS: list[str] = [".csv", ".json"]

# 报告生成
MAX_SHAP_FEATURES_DISPLAY: int = 10
MAX_FACTOR_REASONS_DISPLAY: int = 5

# 知识图谱
KG_MAX_PATH_DEPTH: int = 6
KG_TOP_INDUSTRIES: int = 5
