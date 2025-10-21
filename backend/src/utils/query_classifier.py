"""
Query Classification for Tool Routing.

Pre-filters tools based on query intent before LLM invocation.
This reduces the decision space and improves tool selection accuracy.
"""

import re
from enum import Enum
from typing import Any


class QueryIntent(str, Enum):
    """Query intent types."""

    AGGREGATION = "aggregation"  # Calculate statistics (avg, min, max, sum)
    RETRIEVAL = "retrieval"  # Get raw data (list, show, display)
    WORKOUT = "workout"  # Workout-specific queries
    UNKNOWN = "unknown"  # Cannot determine intent


class QueryClassifier:
    """
    Classify user queries to route to appropriate tools.

    Uses keyword matching to determine query intent and recommend tools.
    This provides a deterministic pre-filtering layer before LLM tool selection.
    """

    # Aggregation keywords - mathematical operations
    AGGREGATION_KEYWORDS = [
        r"\baverage\b",
        r"\bmean\b",
        r"\bavg\b",
        r"\bminimum\b",
        r"\bmin\b",
        r"\blowest\b",
        r"\bmaximum\b",
        r"\bmax\b",
        r"\bhighest\b",
        r"\bbest\b",
        r"\bworst\b",
        r"\btotal\b",
        r"\bsum\b",
        r"\bcount\b",
        r"\bstatistics\b",
        r"\bstats\b",
        r"\bcalculate\b",
        r"\bcompute\b",
        r"\bhow many total\b",
        r"\bgive me numbers\b",
    ]

    # Retrieval keywords - viewing raw data
    RETRIEVAL_KEYWORDS = [
        r"\bshow\b",
        r"\bdisplay\b",
        r"\blist\b",
        r"\btrend\b",
        r"\bhistory\b",
        r"\bover time\b",
        r"\bwhat was\b",
        r"\bwhat is\b",
        r"\bwhen was\b",
        r"\bview\b",
        r"\bsee\b",
        r"\bget\b",
        r"\ball\b",
        r"\bevery\b",
    ]

    # Workout keywords - workout-specific
    WORKOUT_KEYWORDS = [
        r"\bworkout\b",
        r"\bexercise\b",
        r"\bactivity\b",
        r"\btrain\b",
        r"\btraining\b",
        r"\bgym\b",
        r"\blast workout\b",
        r"\blast time.*work\b",  # "last time I worked out"
        r"\brecent workout\b",
        r"\bwhen did I work\b",
        r"\bwhen did I exercise\b",
        r"\bwhen was.*workout\b",
        r"\btell me about.*workout\b",
    ]

    def __init__(self):
        """Initialize query classifier."""
        # Compile regex patterns for performance
        self.aggregation_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.AGGREGATION_KEYWORDS
        ]
        self.retrieval_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.RETRIEVAL_KEYWORDS
        ]
        self.workout_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.WORKOUT_KEYWORDS
        ]

    def classify_intent(self, query: str) -> dict[str, Any]:
        """
        Classify query intent using keyword matching.

        Args:
            query: User's question

        Returns:
            Dict with:
                - intent: QueryIntent enum value
                - confidence: Float 0-1 (based on keyword matches)
                - recommended_tools: List of tool names to present to LLM
                - reasoning: Explanation of classification
                - matched_keywords: List of keywords that matched
        """
        query.lower()

        # Count matches for each category
        aggregation_matches = self._count_matches(query, self.aggregation_patterns)
        retrieval_matches = self._count_matches(query, self.retrieval_patterns)
        workout_matches = self._count_matches(query, self.workout_patterns)

        # Decision logic: Priority order matters
        # 1. Workout queries (most specific)
        if workout_matches > 0:
            confidence = min(
                1.0, workout_matches * 0.4
            )  # 1 match = 0.4, 2+ matches = 0.8+
            return {
                "intent": QueryIntent.WORKOUT,
                "confidence": confidence,
                "recommended_tools": ["search_workouts_and_activity"],
                "reasoning": f"Detected {workout_matches} workout keyword(s)",
                "matched_keywords": self._get_matched_keywords(
                    query, self.workout_patterns
                ),
            }

        # 2. Aggregation queries (high priority - our main fix target)
        if aggregation_matches > 0:
            # Strong signal - even 1 aggregation keyword is usually definitive
            confidence = min(
                1.0, aggregation_matches * 0.5
            )  # 1 match = 0.5, 2+ matches = 1.0
            return {
                "intent": QueryIntent.AGGREGATION,
                "confidence": confidence,
                "recommended_tools": ["aggregate_metrics"],
                "reasoning": f"Detected {aggregation_matches} aggregation keyword(s)",
                "matched_keywords": self._get_matched_keywords(
                    query, self.aggregation_patterns
                ),
            }

        # 3. Retrieval queries (default fallback with keywords)
        if retrieval_matches > 0:
            confidence = min(
                0.8, retrieval_matches * 0.3
            )  # Lower confidence, more generic
            return {
                "intent": QueryIntent.RETRIEVAL,
                "confidence": confidence,
                "recommended_tools": ["search_health_records_by_metric"],
                "reasoning": f"Detected {retrieval_matches} retrieval keyword(s)",
                "matched_keywords": self._get_matched_keywords(
                    query, self.retrieval_patterns
                ),
            }

        # 4. No matches - unknown intent (present all tools, let LLM decide)
        return {
            "intent": QueryIntent.UNKNOWN,
            "confidence": 0.0,
            "recommended_tools": [
                "search_health_records_by_metric",
                "search_workouts_and_activity",
                "aggregate_metrics",
            ],
            "reasoning": "No clear keywords detected, presenting all tools",
            "matched_keywords": [],
        }

    def _count_matches(self, query: str, patterns: list[re.Pattern]) -> int:
        """Count how many patterns match in the query."""
        count = 0
        for pattern in patterns:
            if pattern.search(query):
                count += 1
        return count

    def _get_matched_keywords(
        self, query: str, patterns: list[re.Pattern]
    ) -> list[str]:
        """Get list of matched keyword patterns."""
        matches = []
        for pattern in patterns:
            match = pattern.search(query)
            if match:
                matches.append(match.group(0))
        return matches

    def should_filter_tools(
        self, classification: dict[str, Any], threshold: float = 0.5
    ) -> bool:
        """
        Determine if tools should be filtered based on classification confidence.

        Args:
            classification: Result from classify_intent()
            threshold: Confidence threshold for filtering (default 0.5)

        Returns:
            True if we should only present recommended_tools to LLM
            False if we should present all tools
        """
        return classification["confidence"] >= threshold
