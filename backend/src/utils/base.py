"""
Base classes and utilities for AI agent tools.

Provides standardized interfaces, validation, and error handling
for all tools used by AI agents in the Redis wellness application.
"""

import functools
import logging
import time
from datetime import datetime
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """
    Standardized result format for all AI agent tools.

    Ensures consistent response structure for AI agents.
    """

    success: bool
    data: dict[str, Any] | None = None
    message: str = ""
    execution_time_ms: float | None = None
    timestamp: datetime = datetime.now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class ToolError(Exception):
    """
    Standardized error for AI agent tools.

    Provides structured error information without exposing sensitive data.
    """

    def __init__(
        self, message: str, error_code: str = "TOOL_ERROR", details: dict | None = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.timestamp = datetime.now()

    def to_result(self) -> ToolResult:
        """Convert to ToolResult for consistent error responses."""
        return ToolResult(
            success=False,
            message=f"[{self.error_code}] {self.message}",
            data={"error_code": self.error_code, "details": self.details},
            timestamp=self.timestamp,
        )


def validate_tool_input(input_schema: dict[str, Any]):
    """
    Decorator to validate tool input parameters.

    Args:
        input_schema: JSON schema for parameter validation
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # Basic validation - in production would use jsonschema
                required_params = input_schema.get("required", [])
                for param in required_params:
                    if param not in kwargs:
                        raise ToolError(
                            f"Missing required parameter: {param}", "INVALID_INPUT"
                        )

                return func(*args, **kwargs)

            except ToolError:
                raise
            except Exception as e:
                logger.error(f"Tool validation error in {func.__name__}: {str(e)}")
                raise ToolError(
                    "Input validation failed",
                    "VALIDATION_ERROR",
                    {"function": func.__name__},
                )

        return wrapper

    return decorator


def measure_execution_time(func):
    """
    Decorator to measure and log tool execution time.

    Useful for performance comparison between Redis and stateless approaches.
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        try:
            result = func(*args, **kwargs)

            # Add execution time to result if it's a ToolResult
            if isinstance(result, ToolResult):
                execution_time = (time.time() - start_time) * 1000
                result.execution_time_ms = execution_time

                # Log performance metrics (no sensitive data)
                logger.info(f"Tool {func.__name__} executed in {execution_time:.2f}ms")

            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(
                f"Tool {func.__name__} failed after {execution_time:.2f}ms: {str(e)}"
            )
            raise

    return wrapper


def create_success_result(
    data: Any, message: str = "Operation completed successfully"
) -> ToolResult:
    """
    Helper function to create successful ToolResult.

    Args:
        data: Result data to return to AI agent
        message: Success message

    Returns:
        ToolResult indicating success
    """
    return ToolResult(
        success=True,
        data=data if isinstance(data, dict) else {"result": data},
        message=message,
    )


def create_error_result(
    message: str, error_code: str = "TOOL_ERROR", details: dict | None = None
) -> ToolResult:
    """
    Helper function to create error ToolResult.

    Args:
        message: Error message for AI agent
        error_code: Structured error code
        details: Additional error details (non-sensitive)

    Returns:
        ToolResult indicating failure
    """
    return ToolResult(
        success=False,
        message=f"[{error_code}] {message}",
        data={"error_code": error_code, "details": details or {}},
    )


def sanitize_for_ai(
    data: dict[str, Any], privacy_level: str = "safe"
) -> dict[str, Any]:
    """
    Sanitize data for AI agent consumption based on privacy level.

    Args:
        data: Raw data to sanitize
        privacy_level: Level of sanitization ("safe", "anonymous", "minimal")

    Returns:
        Sanitized data safe for AI processing
    """
    if privacy_level == "anonymous":
        # Remove all personal identifiers
        sensitive_keys = ["device", "source_name", "creation_date", "user_id"]
        return {k: v for k, v in data.items() if k not in sensitive_keys}

    elif privacy_level == "minimal":
        # Keep only essential health metrics
        essential_keys = ["record_type", "value", "unit", "start_date"]
        return {k: v for k, v in data.items() if k in essential_keys}

    else:  # "safe" - default
        # Remove only highly sensitive fields
        sensitive_keys = ["raw_metadata", "device_id"]
        return {k: v for k, v in data.items() if k not in sensitive_keys}


class HealthDataValidator:
    """
    Validator for health data to ensure quality and consistency.

    Prevents AI agents from processing invalid or potentially harmful data.
    """

    @staticmethod
    def validate_user_id(user_id: str) -> bool:
        """Validate user ID format."""
        if not user_id or not isinstance(user_id, str):
            return False
        return not (len(user_id) < 3 or len(user_id) > 100)

    @staticmethod
    def validate_file_path(file_path: str) -> bool:
        """Validate file path for security."""
        if not file_path or not isinstance(file_path, str):
            return False

        # Basic security checks
        if ".." in file_path or file_path.startswith("/"):
            return False

        # Must be XML file
        return file_path.endswith(".xml")

    @staticmethod
    def validate_metric_types(metric_types: list[str]) -> bool:
        """Validate health metric type names."""
        if not metric_types or not isinstance(metric_types, list):
            return False

        valid_metrics = {
            "BodyMassIndex",
            "BodyMass",
            "Height",
            "StepCount",
            "DietaryWater",
            "ActiveEnergyBurned",
            "HeartRate",
        }

        return all(metric in valid_metrics for metric in metric_types)


# Performance tracking for Redis vs stateless comparison
class PerformanceTracker:
    """
    Track performance metrics for demonstrating Redis advantages.
    """

    def __init__(self):
        self.metrics = {}

    def start_operation(self, operation_name: str, approach: str):
        """Start tracking an operation."""
        key = f"{operation_name}_{approach}"
        self.metrics[key] = {"start_time": time.time()}

    def end_operation(self, operation_name: str, approach: str, success: bool = True):
        """End tracking and record results."""
        key = f"{operation_name}_{approach}"
        if key in self.metrics:
            duration = time.time() - self.metrics[key]["start_time"]
            self.metrics[key].update(
                {
                    "duration_ms": duration * 1000,
                    "success": success,
                    "end_time": time.time(),
                }
            )

    def get_comparison(self, operation_name: str) -> dict[str, Any]:
        """Get performance comparison between Redis and stateless."""
        redis_key = f"{operation_name}_redis"
        stateless_key = f"{operation_name}_stateless"

        if redis_key not in self.metrics or stateless_key not in self.metrics:
            return {"error": "Insufficient data for comparison"}

        redis_time = self.metrics[redis_key]["duration_ms"]
        stateless_time = self.metrics[stateless_key]["duration_ms"]

        improvement = ((stateless_time - redis_time) / stateless_time) * 100

        return {
            "redis_time_ms": redis_time,
            "stateless_time_ms": stateless_time,
            "improvement_percentage": improvement,
            "redis_faster": redis_time < stateless_time,
        }


# Global performance tracker instance
performance_tracker = PerformanceTracker()
