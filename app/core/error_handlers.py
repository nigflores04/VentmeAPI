"""
Centralized error handling for Ventics AI API.
Provides consistent error responses and automatic logging.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import VenticsAPIException

logger = logging.getLogger(__name__)


def get_request_id(request: Request) -> str:
    """Get or generate request ID for tracking."""
    return getattr(request.state, "request_id", str(uuid.uuid4()))


def create_error_response(
    *,
    status_code: int,
    error_code: str,
    message: str,
    request_id: str,
    details: Dict[str, Any] | None = None
) -> JSONResponse:
    """Create standardized error response."""
    error_payload = {
        "error": {
            "code": error_code,
            "message": message,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }
    
    # Only include details in development/debug mode
    # In production, sensitive details should be logged but not returned
    if details and logger.level <= logging.DEBUG:
        error_payload["error"]["details"] = details
    
    return JSONResponse(
        status_code=status_code,
        content=error_payload
    )


async def ventics_exception_handler(request: Request, exc: VenticsAPIException) -> JSONResponse:
    """Handle custom Ventics API exceptions."""
    request_id = get_request_id(request)
    
    # Log the error with context
    logger.error(
        f"VenticsAPIException: {exc.error_code}",
        extra={
            "request_id": request_id,
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=exc.error_code,
        message=exc.message,
        request_id=request_id,
        details=exc.details
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    request_id = get_request_id(request)
    
    # Map status codes to error codes
    error_code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
        502: "BAD_GATEWAY",
        503: "SERVICE_UNAVAILABLE",
        504: "GATEWAY_TIMEOUT"
    }
    
    error_code = error_code_map.get(exc.status_code, "INTERNAL_SERVER_ERROR")
    
    # Sanitize error message - don't expose internal details
    message = str(exc.detail) if isinstance(exc.detail, str) else "An error occurred"
    
    logger.warning(
        f"HTTPException: {error_code}",
        extra={
            "request_id": request_id,
            "status_code": exc.status_code,
            "error_code": error_code,
            "message": message,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=exc.status_code,
        error_code=error_code,
        message=message,
        request_id=request_id
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic validation errors."""
    request_id = get_request_id(request)
    
    # Extract validation errors
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    # Create user-friendly message
    if len(errors) == 1:
        message = f"Validation error in field '{errors[0]['field']}': {errors[0]['message']}"
    else:
        message = f"Validation failed for {len(errors)} field(s)"
    
    logger.warning(
        "Validation error",
        extra={
            "request_id": request_id,
            "errors": errors,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return create_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="VALIDATION_ERROR",
        message=message,
        request_id=request_id,
        details={"errors": errors}
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = get_request_id(request)
    
    # Log full exception details for debugging
    logger.exception(
        "Unhandled exception",
        extra={
            "request_id": request_id,
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method
        },
        exc_info=exc
    )
    
    # Return generic error to client (don't expose internal details)
    return create_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_SERVER_ERROR",
        message="An unexpected error occurred. Please try again later.",
        request_id=request_id
    )
