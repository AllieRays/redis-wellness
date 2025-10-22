"""
API error handling utilities and middleware.

Provides FastAPI exception handlers, HTTP status mapping, and
standardized API error responses.
"""

import logging
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .exceptions import (
    AuthenticationError,
    BusinessLogicError,
    InfrastructureError,
    ValidationError,
    WellnessError,
    generate_correlation_id,
)

logger = logging.getLogger(__name__)


def map_error_to_status_code(error: WellnessError) -> int:
    """Map wellness errors to appropriate HTTP status codes."""
    if isinstance(error, ValidationError):
        return 400
    elif isinstance(error, AuthenticationError):
        return 401
    elif isinstance(error, BusinessLogicError):
        return 422
    elif isinstance(error, InfrastructureError):
        return 503
    else:
        return 500


def create_api_error(
    code: str,
    message: str,
    status_code: int = 500,
    details: dict[str, Any] = None,
    correlation_id: str = None,
) -> HTTPException:
    """Create standardized FastAPI HTTPException."""
    error_data = {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
            "correlation_id": correlation_id or generate_correlation_id(),
        },
    }

    return HTTPException(status_code=status_code, detail=error_data)


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Middleware to handle unhandled exceptions and add correlation IDs."""

    async def dispatch(self, request: Request, call_next):
        # Generate correlation ID for request
        correlation_id = generate_correlation_id()
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id
            return response

        except Exception:
            # Log unexpected errors
            logger.error(
                f"Unhandled exception in request {correlation_id}",
                exc_info=True,
                extra={"correlation_id": correlation_id},
            )

            # Return standardized error response
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "INTERNAL_SERVER_ERROR",
                        "message": "An unexpected error occurred",
                        "details": {},
                        "correlation_id": correlation_id,
                    },
                },
                headers={"X-Correlation-ID": correlation_id},
            )


async def wellness_exception_handler(
    request: Request, exc: WellnessError
) -> JSONResponse:
    """Handle WellnessError exceptions with proper status codes."""
    status_code = map_error_to_status_code(exc)
    correlation_id = getattr(request.state, "correlation_id", exc.correlation_id)

    # Log error with correlation ID
    logger.error(
        f"WellnessError: {exc.error_code}",
        extra={
            "error_code": exc.error_code,
            "correlation_id": correlation_id,
            "details": exc.details,
        },
        exc_info=status_code >= 500,
    )

    # Don't expose internal details for infrastructure errors
    error_details = exc.details if status_code < 500 else {}
    safe_message = (
        exc.message if status_code < 500 else "Service temporarily unavailable"
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": exc.error_code,
                "message": safe_message,
                "details": error_details,
                "correlation_id": correlation_id,
                "timestamp": exc.timestamp.isoformat(),
            },
        },
        headers={"X-Correlation-ID": correlation_id},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI HTTPException with standardized format."""
    correlation_id = getattr(request.state, "correlation_id", generate_correlation_id())

    # Log HTTP exceptions
    logger.warning(
        f"HTTP Exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "correlation_id": correlation_id,
            "detail": exc.detail,
        },
    )

    # If detail is already our error format, use it
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        content = exc.detail
        # Ensure correlation ID is set
        if "correlation_id" not in content["error"]:
            content["error"]["correlation_id"] = correlation_id
    else:
        # Create standardized format
        content = {
            "success": False,
            "data": None,
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": {},
                "correlation_id": correlation_id,
            },
        }

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers={"X-Correlation-ID": correlation_id},
    )


def setup_exception_handlers(app):
    """Setup all exception handlers for the FastAPI app."""
    app.add_exception_handler(WellnessError, wellness_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Add error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)


# === Validation Helpers ===


def validate_required_fields(data: dict[str, Any], required_fields: list[str]) -> None:
    """Validate that required fields are present and non-empty."""
    for field in required_fields:
        if field not in data:
            raise ValidationError(
                message=f"Missing required field: {field}", field=field
            )
        if data[field] is None or (
            isinstance(data[field], str) and not data[field].strip()
        ):
            raise ValidationError(
                message=f"Field '{field}' cannot be empty",
                field=field,
                value=data[field],
            )


def validate_list_field(
    data: dict[str, Any], field: str, allowed_values: list = None, min_length: int = 1
) -> None:
    """Validate list field constraints."""
    if field not in data:
        return

    value = data[field]
    if not isinstance(value, list):
        raise ValidationError(
            message=f"Field '{field}' must be a list", field=field, value=value
        )

    if len(value) < min_length:
        raise ValidationError(
            message=f"Field '{field}' must contain at least {min_length} item(s)",
            field=field,
            value=value,
        )

    if allowed_values:
        invalid_values = [v for v in value if v not in allowed_values]
        if invalid_values:
            raise ValidationError(
                message=f"Field '{field}' contains invalid values: {invalid_values}",
                field=field,
                value=invalid_values,
            )


def validate_time_period(time_period: str) -> None:
    """Validate time period format."""
    valid_periods = [
        "recent",
        "last_7_days",
        "last_30_days",
        "last_90_days",
        "this_week",
        "last_week",
        "this_month",
        "last_month",
        "early_september",
        "late_august",  # Examples of natural language periods
    ]

    # Allow month names with optional year
    import re

    if re.match(
        r"^(january|february|march|april|may|june|july|august|september|october|november|december)(\s+\d{4})?$",
        time_period.lower(),
    ):
        return

    if time_period.lower() not in [p.lower() for p in valid_periods]:
        raise ValidationError(
            message=f"Invalid time period: {time_period}",
            field="time_period",
            value=time_period,
        )
