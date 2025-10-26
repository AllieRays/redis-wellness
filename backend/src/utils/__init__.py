"""Utility functions for health data processing, validation, and analysis.

Internal modules (not exported):
- intent_router.py: Used internally by intent_bypass_handler.py
"""

# Agent helpers
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

# API error handling (used in main.py)
from .api_errors import setup_exception_handlers

# Base utilities
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

# Conversation fact extraction
from .conversation_fact_extractor import (
    ConversationFactExtractor,
    get_fact_extractor,
)

# Conversion utilities
from .conversion_utils import convert_weight_to_lbs, kg_to_lbs, lbs_to_kg

# Date validation
from .date_validator import DateValidator, get_date_validator

# Exception handling (used across codebase)
from .exceptions import (
    AuthenticationError,
    BusinessLogicError,
    CircuitBreakerOpenError,
    ErrorResponse,
    HealthDataNotFoundError,
    InfrastructureError,
    LLMServiceError,
    MemoryRetrievalError,
    MemoryStorageError,
    RedisConnectionError,
    ToolExecutionError,
    ValidationError,
    WellnessError,
    generate_correlation_id,
    sanitize_user_id,
)
from .exceptions import (
    ToolResult as ExceptionsToolResult,
)

# Health analytics
from .health_analytics import (
    calculate_weight_trends,
    compare_time_periods,
    correlate_metrics,
)

# Intent handling
from .intent_bypass_handler import handle_intent_bypass

# Metric aggregation
from .metric_aggregators import aggregate_metric_values, get_aggregation_summary
from .metric_classifier import (
    AggregationStrategy,
    get_aggregation_strategy,
    should_aggregate_daily,
)

# Numeric validation
from .numeric_validator import NumericValidator, get_numeric_validator

# Pronoun resolution (used in redis_chat.py)
from .pronoun_resolver import PronounResolver, get_pronoun_resolver

# Redis key management
from .redis_keys import RedisKeys, generate_workout_id, parse_workout_id

# Sleep data aggregation (used in sleep tools and indexer)
from .sleep_aggregator import (
    aggregate_sleep_by_date,
    parse_sleep_segments_from_records,
)

# Statistics utilities
from .stats_utils import (
    calculate_basic_stats,
    calculate_linear_regression,
    calculate_moving_average,
    calculate_pearson_correlation,
    calculate_percentage_change,
    compare_periods,
)

# Time utilities
from .time_utils import (
    format_date_utc,
    format_datetime_utc,
    get_utc_timestamp,
    parse_health_record_date,
    parse_time_period,
)

# Token management
from .token_manager import TokenManager, get_token_manager

# Tool deduplication
from .tool_deduplication import ToolCallTracker

# User configuration (used in redis_chat.py and services)
from .user_config import (
    SingleUserConfig,
    extract_user_id_from_session,
    get_user_config,
    get_user_health_data_key,
    get_user_id,
    get_user_memory_key_prefix,
    get_user_redis_key_prefix,
    get_user_session_key,
    validate_user_context,
)

# Validation and retry
from .validation_retry import build_validation_result, validate_and_retry_response

# Verbosity detection
from .verbosity_detector import VerbosityLevel, detect_verbosity

# Workout data fetchers
from .workout_fetchers import (
    fetch_recent_workouts,
    fetch_workouts_from_redis,
    fetch_workouts_in_range,
    get_workout_count,
)

# Workout helpers (used in workout tools)
from .workout_helpers import (
    calculate_max_hr,
    get_heart_rate_during_workout,
    parse_workout_safe,
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
    # API error handling
    "setup_exception_handlers",
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
    # Exception handling
    "WellnessError",
    "BusinessLogicError",
    "InfrastructureError",
    "AuthenticationError",
    "ValidationError",
    "HealthDataNotFoundError",
    "ToolExecutionError",
    "MemoryRetrievalError",
    "MemoryStorageError",
    "RedisConnectionError",
    "LLMServiceError",
    "CircuitBreakerOpenError",
    "ErrorResponse",
    "ExceptionsToolResult",
    "generate_correlation_id",
    "sanitize_user_id",
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
    "DateValidator",
    "get_date_validator",
    "validate_and_retry_response",
    "build_validation_result",
    # Fact extraction
    "ConversationFactExtractor",
    "get_fact_extractor",
    # Intent handling
    "handle_intent_bypass",
    # Pronoun resolution
    "PronounResolver",
    "get_pronoun_resolver",
    # Sleep data aggregation
    "aggregate_sleep_by_date",
    "parse_sleep_segments_from_records",
    # Tool management
    "ToolCallTracker",
    # Token management
    "TokenManager",
    "get_token_manager",
    # User configuration
    "get_user_id",
    "extract_user_id_from_session",
    "validate_user_context",
    "get_user_config",
    "get_user_redis_key_prefix",
    "get_user_health_data_key",
    "get_user_session_key",
    "get_user_memory_key_prefix",
    "SingleUserConfig",
    # Verbosity detection
    "VerbosityLevel",
    "detect_verbosity",
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
    # Workout data
    "fetch_recent_workouts",
    "fetch_workouts_from_redis",
    "fetch_workouts_in_range",
    "get_workout_count",
    "calculate_max_hr",
    "get_heart_rate_during_workout",
    "parse_workout_safe",
]
