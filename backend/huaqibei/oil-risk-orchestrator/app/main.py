"""
FastAPI 应用入口

职责：
    - 创建并配置 FastAPI 应用实例
    - 注册所有路由
    - 配置全局异常处理器
    - 配置 CORS 中间件

禁止：
    - 在此文件中写业务逻辑
    - 在此文件中写 Service 代码
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Any
import json

from app.api.routes import predict, upload, report, health, model_service_placeholder, events, backtest, factor_history, overview
from app.core.settings import settings
from app.core.logger import get_logger
from app.schemas.report_schema import APIResponse, ErrorResponse
from app.core.constants import HTTP_INTERNAL_ERROR
from app.core.errors import BusinessError, BusinessErrorCode
from app.utils.json_utils import generate_request_id

logger = get_logger(__name__)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert non-JSON-serializable objects (e.g. ValueError) into strings."""
    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, tuple):
        return [_to_jsonable(v) for v in value]

    try:
        json.dumps(value)
        return value
    except TypeError:
        return str(value)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理。

    启动时：预加载知识图谱单例。
    关闭时：输出关闭日志。
    """
    # 预加载知识图谱（单例）
    from app.knowledge_graph.graph_query import GraphQuery
    GraphQuery()
    logger.info(
        f"🛢  {settings.APP_NAME} v{settings.APP_VERSION} 启动成功 "
        f"env={settings.ENVIRONMENT}"
    )
    yield
    logger.info("系统正常关闭")


def create_app() -> FastAPI:
    """
    应用工厂函数。

    Returns:
        配置好的 FastAPI 实例。
    """
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "🛢 Oil Risk Intelligence Orchestrator\n\n"
            "银行级油价风险智能分析系统后端 - Model Orchestration Architecture\n\n"
            "**架构分层：**\n"
            "- API层：请求路由与参数校验\n"
            "- Service层：业务逻辑编排\n"
            "- Pipeline层：特征工程\n"
            "- Explain层：SHAP解释与叙述\n"
            "- KnowledgeGraph层：行业传导路径\n"
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ─── CORS 中间件 ──────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ─── 全局异常处理 ─────────────────────────────────────────────
    @app.exception_handler(BusinessError)
    async def business_exception_handler(request: Request, exc: BusinessError) -> JSONResponse:
        request_id = generate_request_id()
        payload = ErrorResponse(
            success=False,
            code=exc.status_code,
            message=exc.code.value,
            details=exc.details if exc.details is not None else {"message": exc.message},
            request_id=request_id,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = generate_request_id()
        payload = ErrorResponse(
            success=False,
            code=422,
            message=BusinessErrorCode.VALIDATION_ERROR.value,
            details=_to_jsonable(exc.errors()),
            request_id=request_id,
        )
        return JSONResponse(status_code=422, content=payload.model_dump())

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        request_id = generate_request_id()
        payload = ErrorResponse(
            success=False,
            code=exc.status_code,
            message=BusinessErrorCode.VALIDATION_ERROR.value,
            details={"message": str(exc.detail)},
            request_id=request_id,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = generate_request_id()
        payload = ErrorResponse(
            success=False,
            code=exc.status_code,
            message=BusinessErrorCode.VALIDATION_ERROR.value,
            details={"message": str(exc.detail)},
            request_id=request_id,
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = generate_request_id()
        logger.error(f"未捕获的异常 path={request.url.path} error={exc}", exc_info=True)
        payload = ErrorResponse(
            success=False,
            code=HTTP_INTERNAL_ERROR,
            message="INTERNAL_SERVER_ERROR",
            details={"message": "服务器内部错误，请联系管理员"},
            request_id=request_id,
        )
        return JSONResponse(status_code=HTTP_INTERNAL_ERROR, content=payload.model_dump())

    # ─── 注册路由 ─────────────────────────────────────────────────
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(predict.router, prefix="/api/v1")
    app.include_router(upload.router, prefix="/api/v1")
    app.include_router(report.router, prefix="/api/v1")
    app.include_router(events.router, prefix="/api/v1")
    app.include_router(backtest.router, prefix="/api/v1")
    app.include_router(factor_history.router, prefix="/api/v1")
    app.include_router(overview.router, prefix="/api/v1")
    app.include_router(model_service_placeholder.router)

    # 根路径重定向到文档
    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        return JSONResponse(
            content={
                "name": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "docs": "/docs",
                "health": "/api/v1/health/",
            }
        )

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
    )
