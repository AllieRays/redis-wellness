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
from .get_health_metrics import create_get_health_metrics_tool
from .get_workout_data import create_get_workout_data_tool
from .memory_tools import create_memory_tools

logger = logging.getLogger(__name__)

__all__ = [
    "create_user_bound_tools",
    "create_get_health_metrics_tool",
    "create_get_workout_data_tool",
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
        1. get_health_metrics - All non-workout health data (heart rate, steps, sleep, weight, etc.)
        2. get_workout_data - ALL workout queries (lists, patterns, progress, comparisons)

    Tool Set (Memory - optional):
        3. get_my_goals - Retrieve user goals and preferences
        4. get_tool_suggestions - Retrieve learned tool-calling patterns
    """
    # Normalize to single user configuration
    user_id = validate_user_context(user_id)

    # Log tool creation
    logger.info(
        f"🔍 Creating user-bound tools for user_id={user_id} (conversation_history ignored)"
    )

    # Create all tools with user binding
    tools = [
        create_get_health_metrics_tool(user_id),  # All non-workout health data
        create_get_workout_data_tool(user_id),  # ALL workout queries (consolidated)
    ]

    # Add memory retrieval tools (for autonomous memory access)
    # Stateless agent sets include_memory_tools=False for baseline comparison
    # Note: Goal setting is handled by pre-router, not tools
    if include_memory_tools:
        memory_tools = create_memory_tools()
        tools.extend(memory_tools)
        logger.info(
            f"✅ Created {len(tools)} TOTAL tools: 2 health (metrics + workouts) + {len(memory_tools)} memory"
        )
    else:
        logger.info(
            f"✅ Created {len(tools)} health tools (metrics + workouts, no memory)"
        )

    return tools
