"""
Custom exception hierarchy for Ventics AI API.
Provides structured error handling with HTTP status codes and error codes.
"""

from typing import Optional, Dict, Any


class VenticsAPIException(Exception):
    """Base exception for all Ventics AI API errors."""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AuthenticationError(VenticsAPIException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=401,
            error_code="AUTHENTICATION_FAILED",
            details=details
        )


class InvalidTokenError(AuthenticationError):
    """Raised when JWT token is invalid."""
    
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message=message, details={"error_code": "INVALID_TOKEN"})


class AuthorizationError(VenticsAPIException):
    """Raised when user lacks permission for an action."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=403,
            error_code="FORBIDDEN",
            details=details
        )


class ValidationError(VenticsAPIException):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if field:
            error_details["field"] = field
        super().__init__(
            message=message,
            status_code=422,
            error_code="VALIDATION_ERROR",
            details=error_details
        )


class ResourceNotFoundError(VenticsAPIException):
    """Raised when a requested resource doesn't exist."""
    
    def __init__(self, resource: str, resource_id: Optional[str] = None):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(
            message=message,
            status_code=404,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "resource_id": resource_id}
        )


class ExternalServiceError(VenticsAPIException):
    """Raised when an external service (Gemini, Paystack, etc.) fails."""
    
    def __init__(self, service: str, message: str = "External service error", details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        error_details["service"] = service
        super().__init__(
            message=f"{service}: {message}",
            status_code=502,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=error_details
        )


class PaymentError(VenticsAPIException):
    """Raised when payment processing fails."""
    
    def __init__(self, message: str, payment_reference: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        error_details = details or {}
        if payment_reference:
            error_details["payment_reference"] = payment_reference
        super().__init__(
            message=message,
            status_code=402,
            error_code="PAYMENT_ERROR",
            details=error_details
        )


class InsufficientCreditsError(VenticsAPIException):
    """Raised when user has insufficient credits."""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            message=f"Insufficient credits. Required: {required}, Available: {available}",
            status_code=402,
            error_code="INSUFFICIENT_CREDITS",
            details={"required": required, "available": available}
        )


class RateLimitError(VenticsAPIException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__(
            message="Rate limit exceeded. Please try again later.",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after": retry_after}
        )


class DatabaseError(VenticsAPIException):
    """Raised when database operation fails."""
    
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details={}
        )
