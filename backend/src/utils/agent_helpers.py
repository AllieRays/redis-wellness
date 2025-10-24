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
        num_predict=1024,  # Reduced from 2048 for faster responses
        timeout=60,
    )


def build_base_system_prompt() -> str:
    """
    Build base system prompt shared by all agents.

    Includes user health context from .env if configured.
    Agents can extend this with mode-specific additions (e.g., memory context).

    Returns:
        str: Base system prompt with optional user health context
    """
    settings = get_settings()

    base_prompt = """You are a health AI assistant with access to the user's Apple Health data.

You have tools to search health records, query workouts, aggregate metrics, and compare time periods.

CRITICAL - TOOL USAGE:
- For "last workout" or "when did I work out" queries → Use search_workouts_and_activity with days_back=30

CRITICAL - Answer the exact question asked:
- When user asks "what day", "which day", or "when" → Identify the DAY OF THE WEEK pattern
- When user asks about patterns or consistency → Analyze and state the pattern, don't list raw data
- When asked about trends → Identify the trend (increasing/decreasing/stable)

Key guidelines:
- Answer directly and concisely - get to the point in 1-2 sentences
- Use day_of_week from tool output - don't calculate it yourself
- Only report data that tools actually return
- Quote returned data exactly (dates, times, numbers)

Example - Day of Week Question:
User: "What day do I consistently push my heart rate when I work out?"
Bad: [Lists all workouts with statistics]
Good: "You consistently work out and push your heart rate on Fridays and Mondays."

Example - Pattern Question:
User: "Am I getting more active?"
Bad: [Lists metrics]
Good: "Yes, your step count has increased 15% over the past month."

Dates/Times:
- All dates are UTC in format "2025-10-22" or "2025-10-22T16:19:34+00:00"
- Present dates naturally to users: "October 22" or "last Friday"
- Never show technical timestamps like "2025-10-22T16:19:34+00:00" to users"""

    # Add user health context if configured
    if settings.user_health_context:
        user_context = f"""

📋 USER HEALTH CONTEXT:
{settings.user_health_context}

Consider this context when analyzing workout data, tracking progress, and providing recommendations.
Reference injury dates, recovery timelines, and goals when relevant to the user's questions.
"""
        base_prompt += user_context

    return base_prompt


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
