"""
Apple Health Query Tools Package - Modular LangChain tool suite.

This package provides LangChain tools for querying Apple Health data from Redis.
All tools are user-bound and automatically inject user context.

Structure:
- get_health_metrics.py - Health metrics with optional statistics
- get_workouts.py - Workout details with heart rate zones
- get_trends.py - Trend analysis and period comparisons
- get_activity_comparison.py - Multi-metric activity comparison
- get_workout_patterns.py - Workout patterns by day (schedule/intensity)
- get_workout_progress.py - Progress tracking between periods

Main Entry Point:
- create_user_bound_tools() - Creates all tools bound to a specific user
"""

import logging

from langchain_core.tools import BaseTool

from ...utils.user_config import validate_user_context
from .get_activity_comparison import create_get_activity_comparison_tool
from .get_health_metrics import create_get_health_metrics_tool
from .get_trends import create_get_trends_tool
from .get_workout_patterns import create_get_workout_patterns_tool
from .get_workout_progress import create_get_workout_progress_tool
from .get_workouts import create_get_workouts_tool
from .memory_tools import create_memory_tools

logger = logging.getLogger(__name__)

__all__ = [
    "create_user_bound_tools",
    "create_get_health_metrics_tool",
    "create_get_workouts_tool",
    "create_get_trends_tool",
    "create_get_activity_comparison_tool",
    "create_get_workout_patterns_tool",
    "create_get_workout_progress_tool",
    "create_memory_tools",
]


def create_user_bound_tools(
    user_id: str,
    conversation_history=None,
    include_memory_tools: bool = True,
) -> list[BaseTool]:
    """
    Create tool instances bound to the single application user.

    In single-user mode, the provided user_id is validated and normalized
    to ensure consistency across the application.

    Args:
        user_id: The user identifier (normalized to single user in this mode)
        conversation_history: Recent conversation messages (unused, for backward compatibility)
        include_memory_tools: Whether to include memory retrieval tools (default: True)
                             Set to False for stateless agent baseline

    Returns:
        List of LangChain tools with validated user_id injected

    Tool Set (Health - always included):
        1. get_health_metrics - Health metrics with optional statistics (raw data OR aggregated)
        2. get_workouts - Workout details with heart rate zones
        3. get_trends - Trend analysis and period comparisons (any metric)
        4. get_activity_comparison - Comprehensive activity comparison (steps, energy, workouts, distance)
        5. get_workout_patterns - Workout patterns by day (schedule OR intensity)
        6. get_workout_progress - Progress tracking between time periods

    Tool Set (Memory - optional):
        7. get_my_goals - Retrieve user goals and preferences
        8. get_tool_suggestions - Retrieve learned tool-calling patterns
    """
    # Normalize to single user configuration
    user_id = validate_user_context(user_id)

    # Log tool creation
    logger.info(
        f"🔍 Creating user-bound tools for user_id={user_id} (conversation_history ignored)"
    )

    # Create all tools with user binding
    tools = [
        create_get_health_metrics_tool(user_id),  # Health metrics (raw OR stats)
        create_get_workouts_tool(user_id),  # Workout details with HR zones
        create_get_trends_tool(user_id),  # Trends and period comparisons
        create_get_activity_comparison_tool(user_id),  # Activity comparison
        create_get_workout_patterns_tool(user_id),  # Workout patterns by day
        create_get_workout_progress_tool(user_id),  # Progress tracking
    ]

    # Add memory retrieval tools (for autonomous memory access)
    # Stateless agent sets include_memory_tools=False for baseline comparison
    # Note: Goal setting is handled by pre-router, not tools
    if include_memory_tools:
        memory_tools = create_memory_tools()
        tools.extend(memory_tools)
        logger.info(
            f"✅ Created {len(tools)} user-bound tools (including {len(memory_tools)} memory tools)"
        )
    else:
        logger.info(
            f"✅ Created {len(tools)} user-bound tools (health only, no memory)"
        )

    return tools
