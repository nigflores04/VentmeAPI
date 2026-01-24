"""
Rate limiting middleware using Redis for distributed rate limiting.
"""

from __future__ import annotations

import time
import logging
from typing import Callable, Optional
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.exceptions import RateLimitError

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Simple in-memory rate limiter (for development/testing)."""
    
    def __init__(self):
        self.requests = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int]:
        """
        Check if request is allowed.
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Maximum requests allowed in window
            window: Time window in seconds
        
        Returns:
            Tuple of (is_allowed, retry_after_seconds)
        """
        now = time.time()
        cutoff = now - window
        
        # Remove old requests
        self.requests[key] = [req_time for req_time in self.requests[key] if req_time > cutoff]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= limit:
            oldest_request = min(self.requests[key])
            retry_after = int(oldest_request + window - now) + 1
            return False, retry_after
        
        # Add current request
        self.requests[key].append(now)
        return True, 0


# Global rate limiter instance
_rate_limiter = InMemoryRateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits on API endpoints."""
    
    # Rate limit configurations (requests per minute)
    RATE_LIMITS = {
        "/v1/auth/login": (5, 60),  # 5 requests per minute
        "/v1/auth/signup": (3, 60),  # 3 requests per minute
        "/v1/auth/verify-email": (5, 60),
        "/v1/auth/resend-code": (3, 60),
        "/v1/generations": (10, 60),  # 10 generations per minute
        "/v1/payments/initialize": (5, 60),
        "default": (100, 60),  # 100 requests per minute for other endpoints
    }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # Get rate limit for this endpoint
        limit, window = self._get_rate_limit(request.url.path)
        
        # Get identifier (IP address or user ID)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        is_allowed, retry_after = _rate_limiter.is_allowed(
            f"{identifier}:{request.url.path}",
            limit,
            window
        )
        
        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier} on {request.url.path}",
                extra={
                    "identifier": identifier,
                    "path": request.url.path,
                    "limit": limit,
                    "window": window,
                    "retry_after": retry_after
                }
            )
            
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests. Please try again later.",
                        "retry_after": retry_after
                    }
                },
                headers={"Retry-After": str(retry_after)}
            )
        
        return await call_next(request)
    
    def _get_rate_limit(self, path: str) -> tuple[int, int]:
        """Get rate limit configuration for path."""
        for pattern, config in self.RATE_LIMITS.items():
            if pattern != "default" and path.startswith(pattern):
                return config
        return self.RATE_LIMITS["default"]
    
    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting."""
        # Try to get user ID from request state (if authenticated)
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            return f"user:{request.state.user.id}"
        
        # Fall back to IP address
        if request.client:
            return f"ip:{request.client.host}"
        
        return "unknown"
