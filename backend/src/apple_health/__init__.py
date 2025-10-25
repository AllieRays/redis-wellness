"""Apple Health Module - Complete Apple Health data processing.

This module provides everything needed to work with Apple Health exports:
- Data models (HealthRecord, HealthDataCollection, etc.)
- Secure XML parsing (parser.py)
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


# Lazy import to avoid circular dependency issues
def create_user_bound_tools(user_id: str):
    from .query_tools import create_user_bound_tools as _create

    return _create(user_id)


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
    # Query Tools (LangChain)
    "create_user_bound_tools",
]
