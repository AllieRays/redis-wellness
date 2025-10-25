"""Utility functions for health data processing, validation, and analysis."""

from .agent_helpers import (
    build_base_system_prompt,
    build_error_response,
    build_message_history,
    build_tool_error_response,
    create_health_llm,
    extract_final_response,
    extract_tool_usage,
    should_continue_tool_loop,
)
from .base import (
    PerformanceTracker,
    ToolError,
    ToolResult,
    create_error_result,
    create_success_result,
    measure_execution_time,
    performance_tracker,
    sanitize_for_ai,
    validate_tool_input,
)
from .conversion_utils import convert_weight_to_lbs, kg_to_lbs, lbs_to_kg
from .health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
    correlate_metrics,
)
from .metric_aggregators import aggregate_metric_values, get_aggregation_summary
from .metric_classifier import (
    AggregationStrategy,
    get_aggregation_strategy,
    should_aggregate_daily,
)
from .numeric_validator import NumericValidator, get_numeric_validator
from .redis_keys import RedisKeys, generate_workout_id, parse_workout_id
from .stats_utils import (
    calculate_basic_stats,
    calculate_linear_regression,
    calculate_moving_average,
    calculate_pearson_correlation,
    calculate_percentage_change,
    compare_periods,
)
from .time_utils import (
    format_date_utc,
    format_datetime_utc,
    get_utc_timestamp,
    parse_health_record_date,
    parse_time_period,
)
from .workout_fetchers import (
    fetch_recent_workouts,
    fetch_workouts_from_redis,
    fetch_workouts_in_range,
    get_workout_count,
)

__all__ = [
    # Agent helpers
    "build_base_system_prompt",
    "build_error_response",
    "build_message_history",
    "build_tool_error_response",
    "create_health_llm",
    "extract_final_response",
    "extract_tool_usage",
    "should_continue_tool_loop",
    # Base utilities
    "PerformanceTracker",
    "ToolError",
    "ToolResult",
    "create_error_result",
    "create_success_result",
    "measure_execution_time",
    "performance_tracker",
    "sanitize_for_ai",
    "validate_tool_input",
    # Conversions
    "convert_weight_to_lbs",
    "kg_to_lbs",
    "lbs_to_kg",
    # Analytics
    "calculate_weight_trends",
    "compare_time_periods",
    "correlate_metrics",
    # Aggregation
    "aggregate_metric_values",
    "get_aggregation_summary",
    "AggregationStrategy",
    "get_aggregation_strategy",
    "should_aggregate_daily",
    # Validation
    "NumericValidator",
    "get_numeric_validator",
    # Redis keys
    "RedisKeys",
    "generate_workout_id",
    "parse_workout_id",
    # Statistics
    "calculate_basic_stats",
    "calculate_linear_regression",
    "calculate_moving_average",
    "calculate_pearson_correlation",
    "calculate_percentage_change",
    "compare_periods",
    # Time utilities
    "format_date_utc",
    "format_datetime_utc",
    "get_utc_timestamp",
    "parse_health_record_date",
    "parse_time_period",
    # Workout fetchers
    "fetch_recent_workouts",
    "fetch_workouts_from_redis",
    "fetch_workouts_in_range",
    "get_workout_count",
]
