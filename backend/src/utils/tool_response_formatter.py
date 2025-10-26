"""
Standardized LLM Tool Response Formatter.

Provides consistent, flattened, semantic response structures across all query tools
to optimize token usage and improve LLM comprehension.

Key principles:
1. Flat structure (max 2 levels deep)
2. Semantic field names (trend_direction vs raw slope)
3. Consistent error handling
4. Human-readable interpretations included
5. Minimal redundancy
"""

from enum import Enum
from typing import Any


class ResponseMode(str, Enum):
    """Response type indicators."""

    SUCCESS = "success"
    ERROR = "error"
    NO_DATA = "no_data"
    PARTIAL = "partial"


class ToolResponseFormatter:
    """
    Centralized formatter for all LLM tool responses.

    Usage:
        formatter = ToolResponseFormatter("get_trends")
        return formatter.success(data, interpretation="Weight is decreasing")
        return formatter.error("No data found", suggestion="Try different dates")
    """

    def __init__(self, tool_name: str):
        """
        Initialize formatter for specific tool.

        Args:
            tool_name: Name of the tool (e.g., "get_trends", "get_workouts")
        """
        self.tool_name = tool_name

    def success(
        self,
        data: dict[str, Any],
        interpretation: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Format successful response.

        Args:
            data: Core response data (flat dict)
            interpretation: Human-readable summary for LLM
            metadata: Optional metadata (count, time_range, etc.)

        Returns:
            Standardized success response

        Example:
            >>> formatter.success(
            ...     data={"average_weight": 170.5, "measurements": 30},
            ...     interpretation="Average weight is 170.5 lbs over 30 measurements",
            ...     metadata={"time_range": "last_30_days"}
            ... )
            {
                "success": True,
                "tool": "get_trends",
                "average_weight": 170.5,
                "measurements": 30,
                "interpretation": "Average weight is 170.5 lbs over 30 measurements",
                "time_range": "last_30_days"
            }
        """
        response = {
            "success": True,
            "tool": self.tool_name,
            **data,  # Flatten data directly into response
        }

        if interpretation:
            response["interpretation"] = interpretation

        if metadata:
            response.update(metadata)

        return response

    def error(
        self,
        error_message: str,
        suggestion: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Format error response with consistent schema.

        Args:
            error_message: What went wrong
            suggestion: How to fix it (optional)
            context: Additional context (metric_type, time_period, etc.)

        Returns:
            Standardized error response

        Example:
            >>> formatter.error(
            ...     "No workout data found",
            ...     suggestion="Try searching more days back",
            ...     context={"days_back": 7, "metric": "workouts"}
            ... )
            {
                "success": False,
                "tool": "get_trends",
                "error": "No workout data found",
                "suggestion": "Try searching more days back",
                "days_back": 7,
                "metric": "workouts"
            }
        """
        response = {
            "success": False,
            "tool": self.tool_name,
            "error": error_message,
        }

        if suggestion:
            response["suggestion"] = suggestion

        if context:
            response.update(context)

        return response

    def no_data(
        self,
        message: str,
        searched_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Format 'no data found' response (not an error, just empty results).

        Args:
            message: Description of what was searched
            searched_context: What was searched (time_range, metric_type, etc.)

        Returns:
            Standardized no-data response

        Example:
            >>> formatter.no_data(
            ...     "No workouts found in the last 7 days",
            ...     searched_context={"time_range": "last_7_days", "metric": "workouts"}
            ... )
            {
                "success": True,
                "tool": "get_trends",
                "has_data": False,
                "message": "No workouts found in the last 7 days",
                "time_range": "last_7_days",
                "metric": "workouts"
            }
        """
        response = {
            "success": True,  # Not an error, just no results
            "tool": self.tool_name,
            "has_data": False,
            "message": message,
        }

        if searched_context:
            response.update(searched_context)

        return response

    @staticmethod
    def flatten_nested_dict(
        nested: dict[str, Any],
        prefix: str = "",
        max_depth: int = 2,
        current_depth: int = 0,
    ) -> dict[str, Any]:
        """
        Flatten nested dictionary for LLM consumption.

        Args:
            nested: Nested dictionary to flatten
            prefix: Prefix for flattened keys
            max_depth: Maximum nesting depth to flatten
            current_depth: Current recursion depth

        Returns:
            Flattened dictionary

        Example:
            >>> flatten_nested_dict({
            ...     "trends": {
            ...         "linear_regression": {"slope": -0.05},
            ...         "statistics": {"count": 30}
            ...     }
            ... })
            {
                "linear_regression_slope": -0.05,
                "statistics_count": 30
            }
        """
        if current_depth >= max_depth:
            return nested

        flattened = {}

        for key, value in nested.items():
            new_key = f"{prefix}_{key}" if prefix else key

            if isinstance(value, dict) and current_depth < max_depth:
                # Recursively flatten
                flattened.update(
                    ToolResponseFormatter.flatten_nested_dict(
                        value, new_key, max_depth, current_depth + 1
                    )
                )
            else:
                flattened[new_key] = value

        return flattened

    @staticmethod
    def format_confidence_from_stats(
        r_squared: float | None = None,
        p_value: float | None = None,
        sample_size: int | None = None,
    ) -> dict[str, Any]:
        """
        Convert statistical metrics into semantic confidence indicators.

        Args:
            r_squared: R² value (0-1)
            p_value: Statistical significance (0-1)
            sample_size: Number of data points

        Returns:
            Dict with semantic confidence fields

        Example:
            >>> format_confidence_from_stats(r_squared=0.85, p_value=0.001, sample_size=30)
            {
                "confidence_level": "high",
                "statistical_significance": "highly_significant",
                "data_quality": "good"
            }
        """
        confidence = {}

        # R² → confidence level
        if r_squared is not None:
            if r_squared > 0.8:
                confidence["confidence_level"] = "high"
            elif r_squared > 0.5:
                confidence["confidence_level"] = "moderate"
            else:
                confidence["confidence_level"] = "low"

        # p-value → significance
        if p_value is not None:
            if p_value < 0.01:
                confidence["statistical_significance"] = "highly_significant"
            elif p_value < 0.05:
                confidence["statistical_significance"] = "significant"
            else:
                confidence["statistical_significance"] = "not_significant"

        # Sample size → data quality
        if sample_size is not None:
            if sample_size >= 30:
                confidence["data_quality"] = "good"
            elif sample_size >= 10:
                confidence["data_quality"] = "moderate"
            else:
                confidence["data_quality"] = "limited"

        return confidence

    @staticmethod
    def format_numeric_value(
        value: float,
        unit: str | None = None,
        precision: int = 1,
        context: str | None = None,
    ) -> dict[str, Any]:
        """
        Format numeric values with both raw and human-readable versions.

        Args:
            value: Numeric value
            unit: Unit of measurement (optional)
            precision: Decimal places
            context: Additional context (e.g., "daily average")

        Returns:
            Dict with value and formatted string

        Example:
            >>> format_numeric_value(87.5, "bpm", precision=1, context="daily average")
            {
                "value": 87.5,
                "formatted": "87.5 bpm (daily average)"
            }
        """
        formatted = f"{value:.{precision}f}"

        if unit:
            formatted += f" {unit}"

        if context:
            formatted += f" ({context})"

        return {"value": round(value, precision), "formatted": formatted}


# Pre-instantiated formatters for common tools
trends_formatter = ToolResponseFormatter("get_trends")
metrics_formatter = ToolResponseFormatter("get_health_metrics")
workouts_formatter = ToolResponseFormatter("get_workouts")
patterns_formatter = ToolResponseFormatter("get_workout_patterns")
progress_formatter = ToolResponseFormatter("get_workout_progress")
