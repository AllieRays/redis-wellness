"""
Standardized API error response models.

Provides consistent error formatting across all API endpoints with:
- Type-safe Pydantic models
- Correlation ID tracking
- Timestamp inclusion
- Structured error details
"""

from datetime import UTC, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

# Generic type for success responses
T = TypeVar("T")


class APIError(BaseModel):
    """
    Standardized API error structure.

    Attributes:
        code: Machine-readable error code (e.g., "VALIDATION_INVALID_INPUT")
        message: Human-readable error message
        details: Additional error context (field name, values, etc.)
        correlation_id: Unique request identifier for tracing
        timestamp: ISO 8601 timestamp when error occurred
    """

    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(
        default_factory=dict, description="Additional error context"
    )
    correlation_id: str = Field(..., description="Request correlation ID for tracing")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC), description="When error occurred"
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


class APIErrorResponse(BaseModel):
    """
    Standard error response wrapper.

    All API error responses follow this structure for consistency.

    Example:
        {
            "success": false,
            "data": null,
            "error": {
                "code": "VALIDATION_INVALID_INPUT",
                "message": "Invalid session_id format",
                "details": {"field": "session_id", "value": ""},
                "correlation_id": "req_a1b2c3d4",
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }
    """

    success: bool = Field(default=False, description="Always false for errors")
    data: None = Field(default=None, description="Always null for errors")
    error: APIError = Field(..., description="Error details")


class APISuccessResponse(BaseModel, Generic[T]):
    """
    Standard success response wrapper.

    All API success responses follow this structure for consistency.

    Example:
        {
            "success": true,
            "data": {"session_id": "demo", "message": "Session cleared"},
            "error": null
        }
    """

    success: bool = Field(default=True, description="Always true for success")
    data: T = Field(..., description="Response payload")
    error: None = Field(default=None, description="Always null for success")


# === Common Error Responses ===


def validation_error(
    message: str,
    field: str | None = None,
    value: Any = None,
    correlation_id: str | None = None,
) -> APIErrorResponse:
    """
    Create validation error response (400).

    Args:
        message: Error description
        field: Field that failed validation
        value: Invalid value provided
        correlation_id: Request tracking ID

    Returns:
        Standardized validation error response
    """
    from ...utils.exceptions import generate_correlation_id

    details = {}
    if field:
        details["field"] = field
    if value is not None:
        details["value"] = str(value)

    return APIErrorResponse(
        error=APIError(
            code="VALIDATION_INVALID_INPUT",
            message=message,
            details=details,
            correlation_id=correlation_id or generate_correlation_id(),
        )
    )


def not_found_error(
    resource: str, identifier: str | None = None, correlation_id: str | None = None
) -> APIErrorResponse:
    """
    Create not found error response (404).

    Args:
        resource: Type of resource not found (e.g., "session", "health_data")
        identifier: Resource identifier
        correlation_id: Request tracking ID

    Returns:
        Standardized not found error response
    """
    from ...utils.exceptions import generate_correlation_id

    details = {"resource": resource}
    if identifier:
        details["identifier"] = identifier

    message = f"{resource.replace('_', ' ').title()} not found"
    if identifier:
        message += f": {identifier}"

    return APIErrorResponse(
        error=APIError(
            code="RESOURCE_NOT_FOUND",
            message=message,
            details=details,
            correlation_id=correlation_id or generate_correlation_id(),
        )
    )


def service_error(
    service: str, reason: str, correlation_id: str | None = None
) -> APIErrorResponse:
    """
    Create service unavailable error response (503).

    Args:
        service: Service name (e.g., "redis", "ollama")
        reason: Why service failed
        correlation_id: Request tracking ID

    Returns:
        Standardized service error response
    """
    from ...utils.exceptions import generate_correlation_id

    return APIErrorResponse(
        error=APIError(
            code="SERVICE_UNAVAILABLE",
            message=f"{service.title()} service unavailable: {reason}",
            details={"service": service, "reason": reason},
            correlation_id=correlation_id or generate_correlation_id(),
        )
    )


def internal_error(
    message: str = "An unexpected error occurred", correlation_id: str | None = None
) -> APIErrorResponse:
    """
    Create internal server error response (500).

    Args:
        message: Error description (keep generic for security)
        correlation_id: Request tracking ID

    Returns:
        Standardized internal error response
    """
    from ...utils.exceptions import generate_correlation_id

    return APIErrorResponse(
        error=APIError(
            code="INTERNAL_SERVER_ERROR",
            message=message,
            details={},
            correlation_id=correlation_id or generate_correlation_id(),
        )
    )
