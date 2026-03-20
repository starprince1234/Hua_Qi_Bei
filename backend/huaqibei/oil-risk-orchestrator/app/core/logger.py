"""
全局日志配置
"""

import logging
import sys


def _configure_root_logger() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    root = logging.getLogger()
    if not root.handlers:
        root.addHandler(handler)
    root.setLevel(logging.INFO)


_configure_root_logger()


def get_logger(name: str) -> logging.Logger:
    """
    获取命名 logger。

    Args:
        name: 模块名称，通常传入 __name__。

    Returns:
        配置好的 Logger 实例。
    """
    return logging.getLogger(name)
