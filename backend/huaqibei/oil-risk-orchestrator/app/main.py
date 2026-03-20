"""
FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import settings
from app.core.constants import API_V1_PREFIX
from app.api.routes import health, predict, report, upload, model_service_placeholder

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(health.router, prefix=API_V1_PREFIX)
app.include_router(predict.router, prefix=API_V1_PREFIX)
app.include_router(report.router, prefix=API_V1_PREFIX)
app.include_router(upload.router, prefix=API_V1_PREFIX)
app.include_router(model_service_placeholder.router, prefix=API_V1_PREFIX)
