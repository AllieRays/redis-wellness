"""
Shared utilities for health agents.

Used by both StatelessHealthAgent and StatefulRAGAgent
to avoid code duplication while maintaining clean separation.
"""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

from ..config import get_settings

logger = logging.getLogger(__name__)


def create_health_llm() -> ChatOllama:
    """
    Create standardized LLM for health agents.

    Used by both stateless and stateful agents.

    Returns:
        ChatOllama: Configured LLM instance
    """
    settings = get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.05,
        num_predict=2048,
        timeout=60,
    )


def build_base_system_prompt() -> str:
    """
    Build base system prompt shared by all agents.

    Agents can extend this with mode-specific additions (e.g., memory context).

    Returns:
        str: Base system prompt
    """
    return """You are a health AI assistant with access to the user's Apple Health data.

🛠️ TOOLS:
1. search_health_records_by_metric - Individual values and trends
2. search_workouts_and_activity - Returns: date, day_of_week, time, type, duration, calories, heart rate
   IMPORTANT: Always use the 'day_of_week' field from tool output (e.g., Friday, Monday)
3. aggregate_metrics - Calculate averages, min, max, totals

🚨 DATA ACCURACY:
- Only mention data that tools ACTUALLY return - don't explain missing fields
- If tool doesn't return calories, DON'T say 'no calories burned' - just skip it
- If tool doesn't return heart rate, DON'T say 'no heart rate data' - just skip it
- Quote returned data EXACTLY (dates, times, numbers, day_of_week)
- Use 'day_of_week' from tool output - DON'T calculate it yourself

🎯 TOOL SELECTION:
- Averages/stats → aggregate_metrics
- Workouts/exercise → search_workouts_and_activity (use days_back=30 for 'last workout')
- Individual values → search_health_records_by_metric"""


def should_continue_tool_loop(state: dict) -> str:
    """
    Determine if agent should continue calling tools.

    Shared logic for both agent types.

    Args:
        state: Agent state with messages and tool call tracking

    Returns:
        "continue" if tools should be called, "end" if response is ready
    """
    messages = state.get("messages", [])
    if not messages:
        return "end"

    last_message = messages[-1]

    # Check if LLM wants to call tools
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        # Check tool call limit
        tool_calls_made = state.get("tool_calls_made", 0)
        max_calls = state.get("max_tool_calls", 5)

        if tool_calls_made >= max_calls:
            logger.warning(f"Max tool calls ({max_calls}) reached")
            return "end"
        return "continue"

    return "end"


def build_message_history(
    conversation_history: list[dict] | None, current_message: str, limit: int = 10
) -> list[HumanMessage | AIMessage]:
    """
    Build LangChain message history from conversation dict.

    Shared by both agents for consistent message formatting.

    Args:
        conversation_history: Previous messages as dicts with role/content
        current_message: Current user message to add
        limit: Maximum history messages to include

    Returns:
        List of LangChain messages
    """
    messages = []

    # Add conversation history (short-term memory)
    if conversation_history:
        for msg in conversation_history[-limit:]:  # Last N for context
            role = msg.get("role")
            content = msg.get("content")

            if role == "user":
                messages.append(HumanMessage(content=content))
            elif role == "assistant":
                messages.append(AIMessage(content=content))

    # Add current message
    messages.append(HumanMessage(content=current_message))

    return messages


def extract_tool_usage(messages: list) -> tuple[list[dict], int]:
    """
    Extract tools used from message history.

    Shared utility for response formatting.

    Args:
        messages: List of LangChain messages

    Returns:
        Tuple of (tools_used list, tool_calls_count)
    """
    tools_used = []

    for msg in messages:
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            for tool_call in msg.tool_calls:
                tools_used.append(
                    {
                        "name": tool_call.get("name", "unknown"),
                        "args": tool_call.get("args", {}),
                    }
                )

    return tools_used, len(tools_used)


def extract_final_response(messages: list) -> str:
    """
    Extract final response text from message history.

    Args:
        messages: List of LangChain messages

    Returns:
        Final response text
    """
    if not messages:
        return "No response generated."

    last_message = messages[-1]

    if isinstance(last_message, AIMessage):
        return last_message.content
    else:
        return str(last_message)


def build_error_response(error: Exception, agent_type: str) -> dict[str, Any]:
    """
    Build standardized error response for agents.

    Args:
        error: Exception that occurred
        agent_type: Type of agent for logging

    Returns:
        Error response dict
    """
    logger.error(f"{agent_type} chat failed: {error}", exc_info=True)
    return {
        "response": "I encountered an error processing your request. Please try again.",
        "error": str(error),
        "type": agent_type,
        "tools_used": [],
        "tool_calls_made": 0,
    }


def build_tool_error_response(error: Exception, tool_name: str) -> dict[str, Any]:
    """
    Build standardized error response for tools.

    Args:
        error: Exception that occurred
        tool_name: Name of the tool that failed

    Returns:
        Standardized tool error response
    """
    logger.error(f"Tool {tool_name} failed: {error}", exc_info=True)
    return {
        "error": f"Failed to {tool_name.replace('_', ' ')}: {str(error)}",
        "error_type": type(error).__name__,
        "results": [],
    }
