"""
日志模块

职责：
    - 提供统一的结构化日志接口
    - 支持控制台 + 文件双路输出
    - 格式可被日志收集系统解析

禁止：
    - 在此文件中写业务逻辑
"""

import logging
import sys
from pathlib import Path


def _build_formatter() -> logging.Formatter:
    """构建统一日志格式。"""
    return logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """
    获取命名 Logger 实例。

    Args:
        name: 模块名称，建议使用 __name__。

    Returns:
        配置好的 Logger 实例。
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger  # 避免重复添加 Handler

    logger.setLevel(logging.DEBUG)
    formatter = _build_formatter()

    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件输出（生产环境）
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "app.log", encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    return logger
