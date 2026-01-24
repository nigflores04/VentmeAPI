"""
Structured logging configuration for Ventics AI API.
Provides JSON-formatted logs with contextual information.
"""

import logging
import sys
import json
from datetime import datetime, timezone
from typing import Any, Dict
from pythonjsonlogger import jsonlogger


class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from logs."""
    
    SENSITIVE_KEYS = {
        'password', 'passwordHash', 'token', 'access_token', 'refresh_token',
        'api_key', 'secret', 'authorization', 'verificationCode',
        'STABILITY_API_KEY', 'OPENAI_API_KEY', 'GEMINI_API_KEY',
        'PAYSTACK_SECRET_KEY', 'JWT_SECRET_KEY', 'S3_SECRET_ACCESS_KEY'
    }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive data from log records."""
        if hasattr(record, 'args') and isinstance(record.args, dict):
            record.args = self._sanitize_dict(record.args)
        
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._sanitize_dict(record.msg)
        
        return True
    
    def _sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively sanitize dictionary data."""
        sanitized = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in self.SENSITIVE_KEYS):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = [
                    self._sanitize_dict(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                sanitized[key] = value
        return sanitized


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional context."""
    
    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add context from extra fields
        if hasattr(record, 'request_id'):
            log_record['request_id'] = record.request_id
        
        if hasattr(record, 'user_id'):
            log_record['user_id'] = record.user_id
        
        if hasattr(record, 'endpoint'):
            log_record['endpoint'] = record.endpoint
        
        if hasattr(record, 'duration_ms'):
            log_record['duration_ms'] = record.duration_ms
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


def setup_logging(log_level: str = "INFO", use_json: bool = True) -> None:
    """
    Configure application logging.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting (recommended for production)
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    # Add sensitive data filter
    sensitive_filter = SensitiveDataFilter()
    console_handler.addFilter(sensitive_filter)
    
    # Set formatter
    if use_json:
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(logger)s %(message)s'
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("app.services.generations_service").setLevel(logging.INFO)
    logging.getLogger("app.services.storage_service").setLevel(logging.INFO)
    logging.getLogger("app.services.auth_service").setLevel(logging.INFO)
    logging.getLogger("app.core.auth").setLevel(logging.INFO)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("aioboto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging configured with level: {log_level}, JSON format: {use_json}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
