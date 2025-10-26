"""
Apple Health Query Tools - AI agent tools for health data analysis.

Provides tools for querying and analyzing Apple Health data stored in Redis.
All tools are user-bound and automatically inject user context.

Active Tools:
- get_health_metrics - All non-sleep, non-workout health data (heart rate, steps, weight, etc.)
- get_sleep_analysis - Sleep data with daily aggregation and efficiency metrics
- get_workout_data - Consolidated workout tool (lists, patterns, progress, comparisons)
- memory_tools - Goal and procedural memory retrieval (get_my_goals, get_tool_suggestions)

Main Entry Point:
- create_user_bound_tools() - Creates all tools bound to a specific user

Architecture:
- Workout queries use a consolidated tool with feature flags (include_patterns, include_progress)
- This reduces token usage while maintaining full functionality
- Shared workout helpers extracted to utils/workout_helpers.py
"""

import logging

from langchain_core.tools import BaseTool

from ...utils.user_config import validate_user_context
from .get_health_metrics import create_get_health_metrics_tool
from .get_sleep_analysis import create_get_sleep_analysis_tool
from .get_workout_data import create_get_workout_data_tool
from .memory_tools import create_memory_tools

logger = logging.getLogger(__name__)

__all__ = [
    "create_user_bound_tools",
    "create_get_health_metrics_tool",
    "create_get_sleep_analysis_tool",
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
        1. get_health_metrics - All non-sleep, non-workout health data (heart rate, steps, weight, etc.)
        2. get_sleep_analysis - Sleep data with daily aggregation and efficiency metrics
        3. get_workout_data - ALL workout queries (lists, patterns, progress, comparisons)

    Tool Set (Memory - optional):
        4. get_my_goals - Retrieve user goals and preferences
        5. get_tool_suggestions - Retrieve learned tool-calling patterns
    """
    # Normalize to single user configuration
    user_id = validate_user_context(user_id)

    # Log tool creation
    logger.info(
        f"🔍 Creating user-bound tools for user_id={user_id} (conversation_history ignored)"
    )

    # Create all tools with user binding
    tools = [
        create_get_health_metrics_tool(
            user_id
        ),  # All non-sleep, non-workout health data
        create_get_sleep_analysis_tool(user_id),  # Sleep data and analysis
        create_get_workout_data_tool(user_id),  # ALL workout queries (consolidated)
    ]

    # Add memory retrieval tools (for autonomous memory access)
    # Stateless agent sets include_memory_tools=False for baseline comparison
    # Note: Goal setting is handled by pre-router, not tools
    if include_memory_tools:
        memory_tools = create_memory_tools()
        tools.extend(memory_tools)
        logger.info(
            f"✅ Created {len(tools)} TOTAL tools: 3 health (metrics + sleep + workouts) + {len(memory_tools)} memory"
        )
    else:
        logger.info(
            f"✅ Created {len(tools)} health tools (metrics + sleep + workouts, no memory)"
        )

    return tools
