"""
Production-grade exception hierarchy and error utilities.

Provides standardized exceptions, error responses, and correlation tracking
for all layers of the wellness application.
"""

import uuid
from datetime import datetime
from typing import Any


def generate_correlation_id() -> str:
    """Generate unique correlation ID for request tracking."""
    return f"req_{uuid.uuid4().hex[:8]}"


def sanitize_user_id(user_id: str) -> str:
    """Sanitize user ID for logging (mask sensitive parts)."""
    if not user_id or len(user_id) <= 4:
        return "***"
    return f"{user_id[:2]}***{user_id[-2:]}"


class WellnessError(Exception):
    """Base exception for all wellness application errors."""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: dict[str, Any] | None = None,
        correlation_id: str | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        self.correlation_id = correlation_id or generate_correlation_id()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp.isoformat(),
        }


class BusinessLogicError(WellnessError):
    """Business logic and validation errors (422 status)."""


class InfrastructureError(WellnessError):
    """Infrastructure and external service errors (503 status)."""


class AuthenticationError(WellnessError):
    """Authentication and authorization errors (401/403 status)."""


class ValidationError(WellnessError):
    """Input validation errors (400 status)."""

    def __init__(self, message: str, field: str = None, value: Any = None, **kwargs):
        super().__init__(
            message=message,
            error_code="VALIDATION_INVALID_INPUT",
            details={
                "field": field,
                "value": str(value) if value is not None else None,
            },
            **kwargs,
        )
        self.field = field
        self.value = value


# === Specific Business Logic Errors ===


class HealthDataNotFoundError(BusinessLogicError):
    """No health data found for the specified criteria."""

    def __init__(
        self, user_id: str, time_period: str = None, metric_types: list = None
    ):
        details = {"user_id": sanitize_user_id(user_id)}
        if time_period:
            details["time_period"] = time_period
        if metric_types:
            details["metric_types"] = metric_types

        super().__init__(
            message="No health data found for the requested criteria",
            error_code="HEALTH_DATA_NOT_FOUND",
            details=details,
        )


class ToolExecutionError(BusinessLogicError):
    """Tool execution failed or timed out."""

    def __init__(self, tool_name: str, reason: str, **kwargs):
        super().__init__(
            message=f"Tool '{tool_name}' execution failed: {reason}",
            error_code="TOOL_EXECUTION_FAILED",
            details={"tool_name": tool_name, "reason": reason},
            **kwargs,
        )


class MemoryRetrievalError(BusinessLogicError):
    """Memory system retrieval failed."""

    def __init__(self, memory_type: str, reason: str = None, **kwargs):
        super().__init__(
            message=f"{memory_type} memory retrieval failed"
            + (f": {reason}" if reason else ""),
            error_code="MEMORY_RETRIEVAL_FAILED",
            details={"memory_type": memory_type, "reason": reason},
            **kwargs,
        )


class MemoryStorageError(BusinessLogicError):
    """Memory system storage failed."""

    def __init__(self, memory_type: str, reason: str = None, **kwargs):
        super().__init__(
            message=f"{memory_type} memory storage failed"
            + (f": {reason}" if reason else ""),
            error_code="MEMORY_STORAGE_FAILED",
            details={"memory_type": memory_type, "reason": reason},
            **kwargs,
        )


# === Infrastructure Errors ===


class RedisConnectionError(InfrastructureError):
    """Redis connection or operation failed."""

    def __init__(self, operation: str, original_error: Exception = None, **kwargs):
        super().__init__(
            message=f"Redis operation failed: {operation}",
            error_code="REDIS_CONNECTION_FAILED",
            details={
                "operation": operation,
                "original_error": str(original_error) if original_error else None,
            },
            **kwargs,
        )


class LLMServiceError(InfrastructureError):
    """LLM service unavailable or failed."""

    def __init__(self, reason: str = "Service unavailable", **kwargs):
        super().__init__(
            message=f"LLM service error: {reason}",
            error_code="LLM_SERVICE_FAILED",
            details={"reason": reason},
            **kwargs,
        )


class CircuitBreakerOpenError(InfrastructureError):
    """Circuit breaker is open, service unavailable."""

    def __init__(self, service_name: str, **kwargs):
        super().__init__(
            message=f"{service_name} circuit breaker is open",
            error_code="CIRCUIT_BREAKER_OPEN",
            details={"service": service_name},
            **kwargs,
        )


# === Response Formatters ===


class ErrorResponse:
    """Standardized error response formatter."""

    @staticmethod
    def create(
        error: WellnessError = None, success: bool = False, data: Any = None
    ) -> dict[str, Any]:
        """Create standardized error response."""
        return {
            "success": success,
            "data": data,
            "error": error.to_dict() if error else None,
        }

    @staticmethod
    def create_success(data: Any) -> dict[str, Any]:
        """Create standardized success response."""
        return {"success": True, "data": data, "error": None}


class ToolResult:
    """Enhanced tool result with error handling."""

    def __init__(
        self,
        success: bool,
        data: Any = None,
        error_code: str = None,
        message: str = "",
        details: dict[str, Any] = None,
        execution_time_ms: float = None,
        correlation_id: str = None,
    ):
        self.success = success
        self.data = data
        self.error_code = error_code
        self.message = message
        self.details = details or {}
        self.execution_time_ms = execution_time_ms
        self.correlation_id = correlation_id or generate_correlation_id()
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "success": self.success,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
        }

        if self.success:
            result["data"] = self.data
            if self.execution_time_ms:
                result["execution_time_ms"] = self.execution_time_ms
        else:
            result["error"] = {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
            }

        return result

    @classmethod
    def success(
        cls,
        data: Any,
        message: str = "Operation completed successfully",
        execution_time_ms: float = None,
    ):
        """Create successful tool result."""
        return cls(
            success=True,
            data=data,
            message=message,
            execution_time_ms=execution_time_ms,
        )

    @classmethod
    def error(cls, error_code: str, message: str, details: dict[str, Any] = None):
        """Create error tool result."""
        return cls(
            success=False, error_code=error_code, message=message, details=details or {}
        )
