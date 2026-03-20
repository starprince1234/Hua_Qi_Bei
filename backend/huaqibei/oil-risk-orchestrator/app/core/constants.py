"""
系统级常量定义

职责：
    - 集中定义不可变业务常量
    - 消灭代码中的魔法数字与魔法字符串

禁止：
    - 在此文件中使用可变配置（可变项请放 settings.py）
    - 在此文件中写逻辑
"""

from enum import Enum


# ─── 风险等级 ────────────────────────────────────────────────────────
class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXTREME = "extreme"

    @property
    def display_cn(self) -> str:
        """返回中文展示名。"""
        mapping = {
            RiskLevel.LOW: "低风险",
            RiskLevel.MEDIUM: "中风险",
            RiskLevel.HIGH: "高风险",
            RiskLevel.EXTREME: "极端风险",
        }
        return mapping[self]


# ─── 预测方向 ────────────────────────────────────────────────────────
class TrendDirection(str, Enum):
    UP = "up"
    DOWN = "down"
    FLAT = "flat"


# ─── 因子分类 ────────────────────────────────────────────────────────
class FactorCategory(str, Enum):
    MACRO = "macro"            # 宏观因子
    SUPPLY = "supply"          # 供给因子
    DEMAND = "demand"          # 需求因子
    GEOPOLITICAL = "geo"       # 地缘政治
    FINANCIAL = "financial"    # 金融因子
    TECHNICAL = "technical"    # 技术面因子


# ─── 行业分类 ────────────────────────────────────────────────────────
class IndustrySector(str, Enum):
    AVIATION = "aviation"
    SHIPPING = "shipping"
    CHEMICAL = "chemical"
    ENERGY = "energy"
    MANUFACTURING = "manufacturing"
    AGRICULTURE = "agriculture"
    FINANCE = "finance"


# ─── 冲击方向 ────────────────────────────────────────────────────────
class ImpactDirection(str, Enum):
    POSITIVE = "positive"     # 油价上涨对该行业利好
    NEGATIVE = "negative"     # 油价上涨对该行业利空
    NEUTRAL = "neutral"       # 中性影响


# ─── 报告模板标识 ────────────────────────────────────────────────────
class ReportTemplate(str, Enum):
    STANDARD = "standard"         # 标准风险报告
    EXECUTIVE = "executive"       # 管理层摘要
    DETAILED = "detailed"         # 详细分析报告


# ─── HTTP 状态码补充 ──────────────────────────────────────────────────
HTTP_OK: int = 200
HTTP_BAD_REQUEST: int = 400
HTTP_UNPROCESSABLE: int = 422
HTTP_INTERNAL_ERROR: int = 500
HTTP_SERVICE_UNAVAILABLE: int = 503

# ─── 特征工程专用常量 ─────────────────────────────────────────────────
FEATURE_NA_FILL_VALUE: float = 0.0
MIN_REQUIRED_ROWS: int = 30        # 最少需要 30 行数据才能构建 lag 特征
MAX_UPLOAD_ROWS: int = 5000        # 单次上传最大行数

# ─── 模型输出字段名 ──────────────────────────────────────────────────
MODEL_FIELD_MEDIAN: str = "median"
MODEL_FIELD_UPPER: str = "upper"
MODEL_FIELD_LOWER: str = "lower"
MODEL_FIELD_SHAP: str = "shap_values"
MODEL_FIELD_CONFIDENCE: str = "confidence_score"
