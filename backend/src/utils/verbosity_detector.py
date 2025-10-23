"""
Lightweight verbosity detection for chat responses.

Simple regex-based detection of user's requested detail level.
"""

import re
from enum import Enum


class VerbosityLevel(str, Enum):
    """Response verbosity levels."""

    CONCISE = "concise"  # Brief, minimal output (default)
    DETAILED = "detailed"  # More analytical, comprehensive response
    COMPREHENSIVE = "comprehensive"  # Full analysis with context


# Verbosity keywords - request for more detail
VERBOSITY_PATTERNS = [
    r"\btell me more\b",
    r"\bmore details\b",
    r"\bmore info\b",
    r"\bmore information\b",
    r"\belaborate\b",
    r"\bexplain\b",
    r"\bexplain more\b",
    r"\bexplain further\b",
    r"\bgo deeper\b",
    r"\bbreak\s+(?:it|that|this|the\s+\w+)\s+down\b",  # "break X down" flexible
    r"\bbreak\s+down\b",  # "break down" simple form
    r"\banalyze\b",
    r"\bin depth\b",
    r"\bin-depth\b",
    r"\bdetailed\b",
    r"\bcomprehensive\b",
    r"\bwhat does that mean\b",
    r"\bwhy is that\b",
    r"\bexpand on\b",
]

# High-intensity phrases that trigger comprehensive mode
HIGH_INTENSITY_PHRASES = [
    "comprehensive",
    "in depth",
    "in-depth",
    "break down",
    "break that down",
    "break it down",
    "analyze",
]


def detect_verbosity(query: str) -> VerbosityLevel:
    """
    Detect requested verbosity level from user query.

    Uses simple regex matching to determine if user wants:
    - CONCISE: Default, brief responses
    - DETAILED: More explanation and context
    - COMPREHENSIVE: Full analysis with deep insights

    Args:
        query: User's question

    Returns:
        VerbosityLevel enum value

    Examples:
        >>> detect_verbosity("What's my weight?")
        VerbosityLevel.CONCISE

        >>> detect_verbosity("Tell me more about my heart rate")
        VerbosityLevel.DETAILED

        >>> detect_verbosity("Break down my activity patterns")
        VerbosityLevel.COMPREHENSIVE
    """
    query_lower = query.lower()

    # Check for any verbosity keywords
    has_verbosity_request = any(
        re.search(pattern, query_lower, re.IGNORECASE) for pattern in VERBOSITY_PATTERNS
    )

    if not has_verbosity_request:
        return VerbosityLevel.CONCISE

    # Check for high-intensity keywords that trigger comprehensive mode
    if any(phrase in query_lower for phrase in HIGH_INTENSITY_PHRASES):
        return VerbosityLevel.COMPREHENSIVE

    return VerbosityLevel.DETAILED
