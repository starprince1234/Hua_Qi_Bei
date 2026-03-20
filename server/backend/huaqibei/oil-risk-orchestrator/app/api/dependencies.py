"""
依赖注入模块

职责：
    - 提供 FastAPI Depends 可用的服务工厂函数
    - 支持通过环境变量切换 mock/real 模式

禁止：
    - 在此文件中写业务逻辑
"""

import os
from app.services.model_client import ModelClient


def get_model_client() -> ModelClient:
    """
    模型客户端工厂函数（依赖注入用）。

    当环境变量 USE_MOCK_MODEL=true 时返回同一个 ModelClient 实例，
    调用 mock_predict 替代真实 API。

    实际路由代码通过 Depends(get_model_client) 注入，
    便于测试时切换 mock 实现。

    Returns:
        ModelClient 实例。
    """
    client = ModelClient()

    # 若设置了 mock 模式，将 predict 方法替换为 mock_predict
    use_mock = os.getenv("USE_MOCK_MODEL", "false").lower() == "true"
    if use_mock:
        client.predict = client.mock_predict  # type: ignore[method-assign]

    return client
