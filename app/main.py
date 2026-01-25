from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.logging_config import setup_logging
from app.core.error_handlers import (
    ventics_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    unhandled_exception_handler
)
from app.core.exceptions import VenticsAPIException
from app.middleware import RequestIDMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.api.v1.routes import api_router
from app.api.v1.endpoints import health
from app.db.client import connect as db_connect, disconnect as db_disconnect
from starlette.exceptions import HTTPException as StarletteHTTPException

# Setup structured logging
use_json_logs = settings.ENVIRONMENT == "production"
setup_logging(log_level="INFO", use_json=use_json_logs)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None
)

# Add middleware (order matters - first added is outermost)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# CORS middleware - MUST be after other middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_origins_list(),  # ✅ Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Register exception handlers
app.add_exception_handler(VenticsAPIException, ventics_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

@app.get("/")
def read_root():
    return {
        "message": "Welcome to Ventics AI API",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT
    }

# Health without version prefix
app.include_router(health.router)

# Versioned API routes
app.include_router(api_router, prefix="/v1")


@app.on_event("startup")
async def on_startup():
    logger.info(
        f"Starting {settings.APP_NAME} v{settings.VERSION}",
        extra={
            "environment": settings.ENVIRONMENT,
            "rate_limiting": settings.RATE_LIMIT_ENABLED,
            "allowed_origins": settings.ALLOWED_ORIGINS
        }
    )
    if settings.DATABASE_URL:
        await db_connect()
        logger.info("Database connection established")
    else:
        logger.warning("No DATABASE_URL configured")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info(f"Shutting down {settings.APP_NAME}")
    if settings.DATABASE_URL:
        await db_disconnect()
        logger.info("Database connection closed")
