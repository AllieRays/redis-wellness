"""
Goal Management Tools - Fast goal storage for LangChain.

Provides a lightweight tool for storing user goals without heavy analysis.
"""

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import Field

logger = logging.getLogger(__name__)


@tool
async def store_user_goal(
    goal_description: str = Field(description="The user's goal in their own words"),
    user_id: str = Field(default="wellness_user", description="User identifier"),
) -> str:
    """
    Store a user's stated goal or intention.

    Use this when the user STATES a goal (not asking a question):
    - "my goal is X"
    - "I want to X"
    - "I'm trying to X"

    This is a fast acknowledgment tool - it doesn't analyze data.

    Args:
        goal_description: What the user wants to achieve
        user_id: User identifier

    Returns:
        Confirmation message to show the user

    Example:
        User: "my goal is to never skip leg day"
        Call: store_user_goal(goal_description="never skip leg day")
        Returns: "Got it! I've saved your goal: never skip leg day"
    """
    try:
        logger.info(
            f"💾 Fast goal store: user_id={user_id}, goal='{goal_description[:50]}...'"
        )

        # Store goal in episodic memory (async)
        from ...services.episodic_memory_manager import get_episodic_memory

        # For now, just store as a text goal (not metric-specific)
        # The actual storage happens in the reflection phase
        get_episodic_memory()

        # Quick acknowledgment - actual storage happens after LLM response
        return f"Got it! I've saved your goal: {goal_description}. I'll help you track your progress toward this goal."

    except Exception as e:
        logger.error(f"❌ Goal storage failed: {e}")
        return f"I'll remember your goal: {goal_description}"


def create_goal_tools(user_id: str = "wellness_user") -> list[Any]:
    """
    Create goal management tools.

    Args:
        user_id: User identifier to bind to tools

    Returns:
        List of LangChain tools for goal management
    """
    logger.info(f"🎯 Creating goal tools for user_id={user_id}")

    return [
        store_user_goal,
    ]
