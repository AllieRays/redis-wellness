"""
Centralized Constants for Redis Wellness.

This module contains all magic numbers, time periods, thresholds, and configuration
constants used throughout the application. Centralizing these values:
- Makes the codebase more maintainable
- Provides clear documentation for each constant
- Makes it easy to tune parameters
- Prevents inconsistencies from duplicate magic numbers

Usage:
    from constants import TTL_SEVEN_MONTHS, MAX_CONTEXT_TOKENS

    redis_client.setex(key, TTL_SEVEN_MONTHS, value)
"""

# ========== Time-To-Live (TTL) Constants ==========

# 7 months in different units (primary TTL for health data and memory)
TTL_SEVEN_MONTHS_SECONDS = 18144000  # 60 * 60 * 24 * 7 * 30 = ~7 months in seconds
TTL_SEVEN_MONTHS_DAYS = 210  # 7 months in days
TTL_ONE_WEEK_SECONDS = 604800  # 7 days in seconds

# Embedding cache TTL
TTL_EMBEDDING_CACHE_SECONDS = 604800  # 7 days (1 week)

# Short durations
TTL_ONE_HOUR_SECONDS = 3600
TTL_ONE_DAY_SECONDS = 86400

# ========== Context Window & Token Management ==========

# Qwen 2.5 7B has ~32k effective context window
MAX_CONTEXT_TOKENS = 24000  # Conservative limit (75% of 32k)
TOKEN_USAGE_THRESHOLD = 0.8  # Trigger trimming at 80% of max
MIN_MESSAGES_TO_KEEP = 2  # Always keep at least 2 recent messages

# ========== Health & Fitness Constants ==========

# Heart Rate Calculations
CONSERVATIVE_MAX_HR = 190  # Age-independent maximum heart rate estimate (bpm)
RESTING_HR_MIN = 40  # Minimum valid resting heart rate (bpm)
RESTING_HR_MAX = 120  # Maximum valid resting heart rate (bpm)
MAX_HR_THEORETICAL = 220  # Theoretical max HR for age calculation (220 - age)

# Heart Rate Zones (as percentage of max HR)
HR_ZONE_1_MAX = 60  # Easy zone: 50-60%
HR_ZONE_2_MAX = 70  # Moderate zone: 60-70%
HR_ZONE_3_MAX = 80  # Tempo zone: 70-80%
HR_ZONE_4_MAX = 90  # Threshold zone: 80-90%
HR_ZONE_5_MAX = 100  # Maximum zone: 90-100%

# BMI Categories (Body Mass Index thresholds)
BMI_UNDERWEIGHT = 18.5
BMI_NORMAL = 25.0
BMI_OVERWEIGHT = 30.0
BMI_OBESE = 35.0

# Weight Conversions
KG_TO_LBS = 2.20462  # 1 kilogram = 2.20462 pounds
LBS_TO_KG = 0.453592  # 1 pound = 0.453592 kilograms

# ========== Workout & Activity Constants ==========

# Default time periods for workout queries
DEFAULT_WORKOUT_SEARCH_DAYS = 7  # Default days back for workout queries
EXTENDED_WORKOUT_SEARCH_DAYS = 30  # Extended search for "last workout" queries
MAX_WORKOUT_SEARCH_DAYS = 90  # Maximum days back to search

# Workout duration thresholds (minutes)
MIN_WORKOUT_DURATION_MINUTES = 5  # Minimum duration to count as workout
MAX_REASONABLE_WORKOUT_HOURS = 10  # Flag workouts longer than this

# Calorie thresholds
MIN_CALORIES_PER_WORKOUT = 10  # Minimum calories to be valid
MAX_REASONABLE_CALORIES = 5000  # Flag if workout burns more than this

# ========== Redis Operation Constants ==========

# Batch sizes for Redis operations
REDIS_SCAN_BATCH_SIZE = 100  # Keys to scan per iteration
REDIS_PIPELINE_BATCH_SIZE = 1000  # Commands to batch in pipeline

# Redis key expiration sentinel
REDIS_NO_EXPIRY = -1  # TTL value indicating key has no expiration

# ========== Agent & LLM Constants ==========

# Tool calling limits
MAX_TOOL_ITERATIONS = 8  # Maximum agent iterations before stopping
MAX_TOOLS_PER_CALL = 5  # Maximum tools agent can call at once

# Response generation
MAX_RESPONSE_LENGTH_CHARS = 2000  # Maximum character length for responses
MIN_RESPONSE_LENGTH_CHARS = 20  # Minimum response length for validity

# ========== Validation Thresholds ==========

# Numeric validation (for anti-hallucination)
NUMERIC_TOLERANCE_PERCENT = 5.0  # Allow 5% deviation in numeric values
MAX_PERCENT_CHANGE = 1000.0  # Flag changes > 1000% as likely hallucination

# Date range validation
MAX_DAYS_BACK = 365 * 2  # Maximum 2 years of historical data
MIN_VALID_YEAR = 2000  # Earliest valid year for health data

# ========== Memory & Caching Constants ==========

# Semantic memory configuration
SEMANTIC_SEARCH_TOP_K = 5  # Number of semantic memories to retrieve
SEMANTIC_SIMILARITY_THRESHOLD = 0.7  # Minimum cosine similarity (0-1)

# Embedding dimensions
EMBEDDING_DIMENSIONS = 1024  # mxbai-embed-large produces 1024-dim vectors

# Cache performance
TARGET_CACHE_HIT_RATE = 0.3  # Target 30%+ cache hit rate
CACHE_WARMUP_SIZE = 100  # Number of entries to pre-cache

# ========== Performance Benchmarks ==========

# Target performance thresholds (milliseconds)
TARGET_REDIS_WRITE_MS = 5.0
TARGET_REDIS_READ_MS = 3.0
TARGET_REDIS_LIST_OP_MS = 5.0
TARGET_EMBEDDING_CACHE_HIT_MS = 10.0
TARGET_EMBEDDING_GENERATION_MS = 500.0  # With GPU
TARGET_EMBEDDING_GENERATION_CPU_MS = 5000.0  # Without GPU
TARGET_MEMORY_STORAGE_MS = 50.0
TARGET_MEMORY_RETRIEVAL_MS = 20.0
TARGET_AGENT_RESPONSE_MS = 5000.0  # Simple query
TARGET_AGENT_RESPONSE_WITH_MEMORY_MS = 8000.0  # With memory

# ========== API & HTTP Constants ==========

# Rate limiting (if implemented)
API_RATE_LIMIT_PER_MINUTE = 60
API_RATE_LIMIT_PER_HOUR = 1000

# Timeouts (seconds)
HTTP_REQUEST_TIMEOUT = 30
OLLAMA_REQUEST_TIMEOUT = 60  # LLM generation can be slow

# ========== Data Quality Constants ==========

# Minimum data points for statistical calculations
MIN_DATA_POINTS_FOR_AVERAGE = 3
MIN_DATA_POINTS_FOR_TREND = 5
MIN_DATA_POINTS_FOR_PATTERN = 10

# Outlier detection
OUTLIER_Z_SCORE_THRESHOLD = 3.0  # Standard deviations from mean
OUTLIER_IQR_MULTIPLIER = 1.5  # Interquartile range multiplier

# ========== Display & Formatting Constants ==========

# Precision for display
DISPLAY_DECIMAL_PLACES = 2  # Default decimal places for metrics
PERCENTAGE_DECIMAL_PLACES = 1  # Decimal places for percentages

# Truncation lengths
MAX_TRUNCATE_QUERY_LENGTH = 200  # Max query length to store
MAX_TRUNCATE_RESPONSE_LENGTH = 500  # Max response length to log

# ========== Application Metadata ==========

APP_NAME = "Redis Wellness"
APP_VERSION = "0.1.0"
API_VERSION = "v1"

# User identifiers
DEFAULT_USER_ID = "wellness_user"

# ========== Export Commonly Used Constants ==========

__all__ = [
    # TTL
    "TTL_SEVEN_MONTHS_SECONDS",
    "TTL_SEVEN_MONTHS_DAYS",
    "TTL_ONE_WEEK_SECONDS",
    "TTL_EMBEDDING_CACHE_SECONDS",
    # Context
    "MAX_CONTEXT_TOKENS",
    "TOKEN_USAGE_THRESHOLD",
    "MIN_MESSAGES_TO_KEEP",
    # Heart Rate
    "CONSERVATIVE_MAX_HR",
    "HR_ZONE_1_MAX",
    "HR_ZONE_2_MAX",
    "HR_ZONE_3_MAX",
    "HR_ZONE_4_MAX",
    # BMI
    "BMI_UNDERWEIGHT",
    "BMI_NORMAL",
    "BMI_OVERWEIGHT",
    # Workouts
    "DEFAULT_WORKOUT_SEARCH_DAYS",
    "EXTENDED_WORKOUT_SEARCH_DAYS",
    # Agent
    "MAX_TOOL_ITERATIONS",
    # Validation
    "NUMERIC_TOLERANCE_PERCENT",
    # Memory
    "SEMANTIC_SEARCH_TOP_K",
    "EMBEDDING_DIMENSIONS",
    # Performance
    "TARGET_REDIS_WRITE_MS",
    "TARGET_EMBEDDING_CACHE_HIT_MS",
]
