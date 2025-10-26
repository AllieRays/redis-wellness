"""
Memory Retrieval Tools - LangChain tools for user goals and tool suggestions.

These tools allow the LLM to autonomously decide when to retrieve:
- User goals and preferences (get_my_goals)
- Tool usage suggestions based on learned patterns (get_tool_suggestions)

Memory retrieval is autonomous - the LLM decides when context is needed,
rather than forcing memory retrieval upfront (like traditional RAG).

Following the Redis AI Resources pattern:
https://github.com/redis-developer/redis-ai-resources/blob/main/python-recipes/agents/03_memory_agent.ipynb
"""

import logging
from typing import Any

from langchain_core.tools import tool
from pydantic import Field

logger = logging.getLogger(__name__)


@tool
async def get_my_goals(
    query: str = Field(
        description="Query to search for goals (e.g., 'weight goal', 'fitness goal')"
    ),
    top_k: int = Field(default=3, description="Number of goals to retrieve"),
) -> str:
    """
    Get your stored goals and preferences.

    USE WHEN user asks:
    - "What's my goal?"
    - "What did I say my target was?"
    - "Do I have any fitness goals?"

    DO NOT USE for:
    - Factual health data → use get_health_metrics instead

    Args:
        query: What goal to search for
        top_k: Number of goals to return

    Returns:
        Your stored goals, or message if none found

    Example:
        "Weight goal: 125 lbs"
    """
    try:
        # Import here to avoid circular dependencies
        from ...services.episodic_memory_manager import get_episodic_memory

        # Hardcode user_id for single-user application
        user_id = "wellness_user"

        logger.info(
            f"🧠 Tool called: get_my_goals(query='{query[:50]}...', user_id={user_id}, top_k={top_k})"
        )

        # Get memory manager singleton instance
        memory_manager = get_episodic_memory()

        # Retrieve memories
        result = await memory_manager.retrieve_goals(
            user_id=user_id,
            query=query,
            top_k=top_k,
        )

        context = result.get("context")
        hits = result.get("hits", 0)

        if context:
            logger.info(f"✅ Retrieved {hits} goals")
            return context
        else:
            logger.info("ℹ️ No goals found")
            return "No goals found. You haven't set any goals yet."

    except Exception as e:
        logger.error(f"❌ Goal retrieval failed: {e}")
        return f"Error retrieving goals: {str(e)}"


@tool
async def get_tool_suggestions(
    query: str = Field(
        description="Query to get tool suggestions for (e.g., 'weight trend analysis')"
    ),
    top_k: int = Field(default=3, description="Number of suggestions to retrieve"),
) -> str:
    """
    Get tool suggestions based on learned successful patterns.

    Get suggestions for which tools to use based on what worked before.

    Returns:
    - Suggested tools for this type of query
    - Success rates of those tool combinations
    - Reasoning for the suggestions

    Args:
        query: What workflow pattern to search for
        top_k: Number of patterns to return

    Returns:
        Formatted string with tool suggestions and reasoning, or empty if none found

    Example:
        "For weight trend queries, use: get_health_metrics, get_trends (90% success)"
    """
    try:
        # Import here to avoid circular dependencies
        from ...services.procedural_memory_manager import get_procedural_memory

        logger.info(
            f"🔧 Tool called: get_tool_suggestions(query='{query[:50]}...', top_k={top_k})"
        )

        # Get memory manager singleton instance
        memory_manager = get_procedural_memory()

        # Retrieve patterns
        result = await memory_manager.retrieve_patterns(
            query=query,
            top_k=top_k,
        )

        patterns = result.get("patterns", [])
        plan = result.get("plan")

        if patterns and plan:
            suggested_tools = plan.get("suggested_tools", [])
            reasoning = plan.get("reasoning", "")
            confidence = plan.get("confidence", 0.0)

            logger.info(f"✅ Retrieved {len(patterns)} tool suggestions")

            response = f"Suggested tools: {', '.join(suggested_tools)}\n"
            response += f"Reasoning: {reasoning}\n"
            response += f"Confidence: {confidence:.0%}"
            return response
        else:
            logger.info("ℹ️ No tool suggestions found")
            return "No tool suggestions found for this query. Proceed with your best judgment."

    except Exception as e:
        logger.error(f"❌ Tool suggestion retrieval failed: {e}")
        return f"Error retrieving tool suggestions: {str(e)}"


def create_memory_tools(user_id: str = "wellness_user") -> list[Any]:
    """
    Create memory retrieval tools bound to a user.

    Args:
        user_id: User identifier to bind to tools

    Returns:
        List of LangChain tools for memory retrieval
    """
    logger.info(f"🧠 Creating memory tools for user_id={user_id}")

    # Tools hardcode user_id internally for single-user application
    return [
        get_my_goals,
        get_tool_suggestions,
    ]
