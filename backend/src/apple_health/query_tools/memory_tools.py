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

logger = logging.getLogger(__name__)


@tool
async def get_my_goals(
    query: str,
    top_k: int = 3,
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
        query: Query to search for goals (e.g., 'weight goal', 'fitness goal')
        top_k: Number of goals to return (default: 3)

    Returns:
        Formatted goals string with one goal per line, or "No goals found." if none exist.

    Example:
        "Weight goal: 125 lbs\nBMI goal: 22"
    """
    try:
        # Import here to avoid circular dependencies
        from ...services.episodic_memory_manager import get_episodic_memory

        # Hardcode user_id for single-user application
        user_id = "wellness_user"

        # Log with proper truncation
        query_display = f"{query[:47]}..." if len(query) > 50 else query
        logger.info(
            f"🧠 Tool called: get_my_goals(query='{query_display}', top_k={top_k})"
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
            logger.info(f"✅ Retrieved {hits} goal(s)")
            return context
        else:
            logger.info("🔍 No goals found")
            return "No goals found."

    except Exception as e:
        logger.error(f"❌ Goal retrieval failed: {e}")
        return f"Error: {str(e)}"


@tool
async def get_tool_suggestions(
    query: str,
    top_k: int = 3,
) -> str:
    """
    Retrieve tool suggestions based on successful past patterns.

    Analyzes query similarity to find which tool combinations worked well before.
    Uses semantic search over historical workflow patterns.

    Args:
        query: Query to analyze (e.g., 'weight trend analysis')
        top_k: Number of patterns to retrieve (default: 3)

    Returns:
        Structured string with:
        - Tools: Comma-separated list of suggested tools
        - Reasoning: Why these tools were suggested
        - Confidence: Success rate as percentage

        Returns "No tool suggestions found." if no patterns match.

    Example:
        "Tools: get_health_metrics, get_trends
        Reasoning: Based on previous successful workflow (success: 95%)
        Confidence: 95%"
    """
    try:
        # Import here to avoid circular dependencies
        from ...services.procedural_memory_manager import get_procedural_memory

        # Log with proper truncation
        query_display = f"{query[:47]}..." if len(query) > 50 else query
        logger.info(
            f"🔧 Tool called: get_tool_suggestions(query='{query_display}', top_k={top_k})"
        )

        # Get memory manager singleton instance
        memory_manager = get_procedural_memory()
        if not memory_manager:
            logger.warning("⚠️ Procedural memory manager not available")
            return "No tool suggestions found."

        # Retrieve patterns
        result = await memory_manager.retrieve_patterns(
            query=query,
            top_k=top_k,
        )

        plan = result.get("plan")
        if not plan:
            logger.info("🔍 No tool suggestions found")
            return "No tool suggestions found."

        suggested_tools = plan.get("suggested_tools", [])
        reasoning = plan.get("reasoning", "")
        confidence = plan.get("confidence", 0.0)

        if not suggested_tools:
            logger.info("🔍 No tool suggestions in plan")
            return "No tool suggestions found."

        logger.info(f"✅ Retrieved {len(suggested_tools)} tool suggestion(s)")

        # Structured format for better LLM parsing
        tools_list = ", ".join(suggested_tools)
        return (
            f"Tools: {tools_list}\nReasoning: {reasoning}\nConfidence: {confidence:.0%}"
        )

    except Exception as e:
        logger.error(f"❌ Tool suggestion retrieval failed: {e}")
        return f"Error: {str(e)}"


def create_memory_tools() -> list[Any]:
    """
    Create memory retrieval tools for LLM agents.

    Returns list of LangChain tools that allow the LLM to:
    - Retrieve user goals and preferences (get_my_goals)
    - Get tool usage suggestions from past patterns (get_tool_suggestions)

    Note: Single-user application, so user_id is hardcoded to 'wellness_user'.

    Returns:
        List of LangChain tools for memory retrieval
    """
    logger.info("🧠 Creating memory tools")

    return [
        get_my_goals,
        get_tool_suggestions,
    ]
