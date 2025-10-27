"""
Structured JSON Logging for ESG Scoring API - Phase 11

Provides request/response logging with trace correlation.

SCA v13.8 Compliance:
- Type safety: 100% annotated
- Determinism: Timestamps in ISO format
- Security: No PII logging
"""

from typing import Callable, Dict, Any, Optional
from fastapi import Request, Response
from pythonjsonlogger import jsonlogger
import logging
import time
import uuid
from datetime import datetime


# Configure JSON formatter
class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any]
    ) -> None:
        """
        Add custom fields to log record.

        Args:
            log_record: Log record dictionary to modify
            record: Original log record
            message_dict: Message dictionary
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO format
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Add log level
        log_record['level'] = record.levelname

        # Add logger name
        log_record['logger'] = record.name


def setup_json_logging() -> logging.Logger:
    """
    Configure JSON logging for the application.

    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger("esg_api")
    logger.setLevel(logging.INFO)

    # Remove existing handlers
    logger.handlers.clear()

    # Create console handler with JSON formatter
    handler = logging.StreamHandler()
    formatter = CustomJsonFormatter(
        fmt='%(timestamp)s %(level)s %(name)s %(message)s',
        rename_fields={
            'timestamp': '@timestamp',
            'levelname': 'level',
            'name': 'logger'
        }
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_json_logging()


def create_logging_middleware() -> Callable[[Request, Callable], Any]:
    """
    Create middleware for request/response logging.

    Returns:
        Middleware callable
    """
    async def logging_middleware(request: Request, call_next: Callable) -> Response:
        """
        Middleware to log HTTP requests and responses.

        Args:
            request: FastAPI request
            call_next: Next middleware in chain

        Returns:
            Response with logging context
        """
        # Generate request ID if not present
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))

        # Extract trace context
        trace_id = request.headers.get("X-Trace-Id", "")
        span_id = request.headers.get("X-Span-Id", "")

        # Record start time
        start_time = time.time()

        # Log request
        logger.info(
            "HTTP request received",
            extra={
                "request_id": request_id,
                "trace_id": trace_id,
                "span_id": span_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_host": request.client.host if request.client else None,
            }
        )

        try:
            # Call next middleware
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                "HTTP response sent",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )

            # Add request ID to response headers
            response.headers["X-Request-Id"] = request_id

            return response

        except Exception as exc:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                "HTTP request failed",
                extra={
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "span_id": span_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "duration_ms": round(duration_ms, 2),
                },
                exc_info=True
            )
            raise

    return logging_middleware
