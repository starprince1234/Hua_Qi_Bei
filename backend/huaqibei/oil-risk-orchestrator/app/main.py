"""
FastAPI 应用入口 — Oil Risk Intelligence Orchestrator
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.settings import get_settings
from app.core.errors import register_error_handlers
from app.api.routes import health, upload, predict, report, model_service_placeholder

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="油价风险智能预测系统 — Orchestrator API",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error handlers
register_error_handlers(app)

# Routers
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(predict.router)
app.include_router(report.router)
app.include_router(model_service_placeholder.router)

