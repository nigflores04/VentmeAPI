<<<<<<< HEAD
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
=======
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timezone
import logging
import sys
from app.core.config import settings
from app.api.v1.routes import api_router
from app.api.v1.endpoints import health
from app.db.client import connect as db_connect, disconnect as db_disconnect
# from app.db import client as db_client


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s',
    # format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Get the root logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set specific loggers to appropriate levels
logging.getLogger("app.services.generations_service").setLevel(logging.INFO)
logging.getLogger("app.services.storage_service").setLevel(logging.INFO)
logging.getLogger("uvicorn").setLevel(logging.INFO)
logging.getLogger("fastapi").setLevel(logging.INFO)

# Reduce noise from third-party libraries
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)
logging.getLogger("aioboto3").setLevel(logging.WARNING)

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],   
)

@app.get("/")
def read_root():
    return {"message": "Welcome to Ventics AI API"}
>>>>>>> origin/master

# Health without version prefix
app.include_router(health.router)

# Versioned API routes
app.include_router(api_router, prefix="/v1")


<<<<<<< HEAD
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
=======
def _error_code_from_status(status_code: int) -> str:
    mapping = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "RESOURCE_NOT_FOUND",
        409: "CONFLICT",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT",
    }
    return mapping.get(status_code, "INTERNAL_SERVER_ERROR")


def _error_envelope(*, status_code: int, message: str, code: str | None = None) -> JSONResponse:
    payload = {
        "message": message,
        "status": "error"
    }
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):  # type: ignore[override]
    # exc.detail can be str or any; standardize to string
    print(exc.detail)
    message = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return _error_envelope(status_code=exc.status_code, message=message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):  # type: ignore[override]
    # Summarize validation errors into a single message
    message = "; ".join([f"{e['loc']}: {e['msg']}" for e in exc.errors()])
    return _error_envelope(status_code=422, message=message)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):  # type: ignore[override]
    # Log unhandled exceptions
    logger.exception(f"Unhandled exception: {str(exc)}")
    return _error_envelope(status_code=500, message=str(exc))


@app.on_event("startup")
async def on_startup():
    logger.info("Starting Ventics AI API")
    if settings.DATABASE_URL:
        await db_connect()
>>>>>>> origin/master


@app.on_event("shutdown")
async def on_shutdown():
<<<<<<< HEAD
    logger.info(f"Shutting down {settings.APP_NAME}")
    if settings.DATABASE_URL:
        await db_disconnect()
        logger.info("Database connection closed")
=======
    logger.info("Shutting down Ventics AI API")
    if settings.DATABASE_URL:
        await db_disconnect()
>>>>>>> origin/master
