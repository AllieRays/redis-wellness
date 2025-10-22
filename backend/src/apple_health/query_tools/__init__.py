"""
Apple Health Query Tools Package - Modular LangChain tool suite.

This package provides LangChain tools for querying Apple Health data from Redis.
All tools are user-bound and automatically inject user context.

Structure:
- search_health_records.py - Health metric search tool
- search_workouts.py - Workout and activity search tool
- apple_health_statistics.py - Statistics and aggregation tool
- apple_health_trends_and_comparisons.py - Advanced analytics (trends, comparisons)
- compare_activity.py - Multi-metric activity comparison

Main Entry Point:
- create_user_bound_tools() - Creates all tools bound to a specific user
"""

import logging

from langchain_core.tools import BaseTool

from ...utils.user_config import validate_user_context
from .apple_health_statistics import create_aggregate_metrics_tool
from .apple_health_trends_and_comparisons import (
    create_compare_periods_tool,
    create_weight_trends_tool,
)
from .compare_activity import create_compare_activity_tool
from .progress_tracking import create_progress_tracking_tool
from .search_health_records import create_search_health_records_tool
from .search_workouts import create_search_workouts_tool
from .workout_patterns import (
    create_intensity_analysis_tool,
    create_workout_schedule_tool,
)

logger = logging.getLogger(__name__)

__all__ = [
    "create_user_bound_tools",
    "create_search_health_records_tool",
    "create_search_workouts_tool",
    "create_aggregate_metrics_tool",
    "create_weight_trends_tool",
    "create_compare_periods_tool",
    "create_compare_activity_tool",
    "create_workout_schedule_tool",
    "create_intensity_analysis_tool",
    "create_progress_tracking_tool",
]


def create_user_bound_tools(user_id: str, conversation_history=None) -> list[BaseTool]:
    """
    Create tool instances bound to the single application user.

    In single-user mode, the provided user_id is validated and normalized
    to ensure consistency across the application.

    Args:
        user_id: The user identifier (normalized to single user in this mode)
        conversation_history: Recent conversation messages (unused, for backward compatibility)

    Returns:
        List of LangChain tools with validated user_id injected

    Tool Set:
        1. search_health_records_by_metric - Query health metrics (weight, BMI, HR, steps)
        2. search_workouts_and_activity - Query workout data with heart rate zones
        3. aggregate_metrics - Calculate statistics (avg, min, max, sum, count)
        4. calculate_weight_trends_tool - Weight trend analysis with regression
        5. compare_time_periods_tool - Period-over-period comparisons (single metric)
        6. compare_activity_periods_tool - Comprehensive activity comparison (steps, energy, workouts, distance)
        7. get_workout_schedule_analysis - Analyze workout patterns by day of week
        8. analyze_workout_intensity_by_day - Compare workout intensity across days
        9. get_workout_progress - Track progress between time periods
    """
    # Normalize to single user configuration
    user_id = validate_user_context(user_id)

    # Log tool creation
    logger.info(
        f"🔍 Creating user-bound tools for user_id={user_id} (conversation_history ignored)"
    )

    # Create all tools with user binding
    tools = [
        create_search_health_records_tool(user_id),  # All metric queries
        create_search_workouts_tool(user_id),  # All workout queries
        create_aggregate_metrics_tool(user_id),  # Statistics and aggregations
        create_weight_trends_tool(user_id),  # Weight trend analysis with regression
        create_compare_periods_tool(
            user_id
        ),  # Period-over-period comparisons (single metric)
        create_compare_activity_tool(user_id),  # Comprehensive activity comparison
        create_workout_schedule_tool(user_id),  # Workout pattern analysis by day
        create_intensity_analysis_tool(user_id),  # Workout intensity by day comparison
        create_progress_tracking_tool(user_id),  # Progress tracking between periods
    ]

    logger.info(f"✅ Created {len(tools)} user-bound tools")
    return tools
