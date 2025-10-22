"""Apple Health Module - Complete Apple Health data processing.

This module provides everything needed to work with Apple Health exports:
- Data models (HealthRecord, HealthDataCollection, etc.)
- Secure XML parsing (parser.py)
- Data processors (processors.py) - parse files and generate insights
- LangChain agent tools (query_tools/) - query health data from Redis
"""

from .models import (
    ActivitySummary,
    HealthDataCollection,
    HealthMetricType,
    HealthRecord,
    PrivacyLevel,
    UserProfile,
    WorkoutSummary,
)
from .parser import AppleHealthParser, ParsingError
from .processors import generate_health_insights, parse_health_file
from .query_tools import create_user_bound_tools

__all__ = [
    # Models
    "HealthDataCollection",
    "HealthMetricType",
    "HealthRecord",
    "PrivacyLevel",
    "UserProfile",
    "WorkoutSummary",
    "ActivitySummary",
    # Parser
    "AppleHealthParser",
    "ParsingError",
    # Processors
    "parse_health_file",
    "generate_health_insights",
    # Query Tools (LangChain)
    "create_user_bound_tools",
]
