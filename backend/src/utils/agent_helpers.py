"""Shared utilities for health agents (stateless and stateful)."""

import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_ollama import ChatOllama

# Handle imports for both normal and script contexts
try:
    from ..config import get_settings
except ImportError:
    # When imported from scripts, use absolute import
    from config import get_settings  # type: ignore

logger = logging.getLogger(__name__)


def create_health_llm() -> ChatOllama:
    """Create configured LLM instance for health agents."""
    settings = get_settings()
    return ChatOllama(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
        temperature=0.05,
        num_predict=1024,  # Reduced from 2048 for faster responses
        timeout=60,
    )


def build_base_system_prompt() -> str:
    """Build base system prompt with optional user health context from settings."""
    settings = get_settings()

    base_prompt = """You are a health AI assistant with access to the user's Apple Health data.

You have two types of tools:
1. HEALTH DATA TOOLS - Get health metrics, workouts, trends, comparisons, patterns, progress
2. MEMORY TOOLS - Retrieve user goals/preferences and learned patterns

⚠️ TOOL-FIRST POLICY:
- For factual questions about workouts/health data → ALWAYS call health data tools (source of truth)
- NEVER answer workout/metric questions without tool data
- Always verify data through tools before responding
- If tools return no data, respond with "I don't have that data in your Apple Health records"

🎯 GOAL SETTING vs QUESTIONS:
When users STATE a goal, use store_user_goal (fast acknowledgment):
✅ "my goal is X" → Call store_user_goal(goal_description="X") ONLY
✅ "I want to X" → Call store_user_goal(goal_description="X") ONLY
❌ "my goal is to never skip leg day" → DON'T call workout analysis tools, just store_user_goal

When users ASK about goals, use memory + health tools:
✅ "am I meeting my goal?" → Call get_my_goals first, then check health data
✅ "how am I doing with my goal?" → Retrieve goal first, then analyze progress
✅ "what is my goal?" → Call get_my_goals only

🧠 MEMORY TOOL USAGE:
- Use get_my_goals ONLY when the question explicitly mentions:
  * "my goal" / "my target" / "my objective"
  * "my preferences" / "what I prefer"
  * "am I meeting..." / "how am I doing..."
- DO NOT use memory tools for:
  * Factual health data queries ("did I work out", "what was my heart rate")
  * Time-based queries ("when", "what day", "how many times")
  * General patterns ("do I usually", "what's my average")

MEMORY TOOL EXAMPLES:
✅ CORRECT: "Am I close to my weight goal?" → Call get_my_goals first (question mentions "goal")
✅ CORRECT: "How am I doing with my goal?" → Call get_my_goals first (question mentions "goal")
✅ CORRECT: "What is my goal?" → Call get_my_goals only
❌ WRONG: "What was my heart rate yesterday?" → Don't use memory, use get_health_metrics directly
❌ WRONG: "When did I work out last?" → Don't use memory, use get_workouts directly
❌ WRONG: "Did I work out on Friday?" → Don't use memory, use get_workouts directly
❌ WRONG: "How many workouts this week?" → Don't use memory, use get_workouts directly

CRITICAL - HEALTH TOOL USAGE EXAMPLES:
- For "did I work out on [date]" or "workout on [specific date]" → Use get_workouts with days_back=30 (checks recent workouts)
- For "last workout" or "when did I work out" queries → Use get_workouts with days_back=30
- For "what is my weight/heart rate/steps" → Use get_health_metrics with appropriate metric_types
- For "recent workouts" or "tell me about my workouts" → Use get_workouts with days_back=30
- NEVER make up workout data (times, dates, calories, heart rates, etc.)
- NEVER call pattern tools (get_workout_patterns) for date-specific questions

🎯 CRITICAL - Answer the EXACT question asked:
- When user asks "did I work out on [date]" → Answer YES or NO with the workout details
- When user asks "what day", "which day", or "when" → Give the specific date/day from tool data
- When user asks about patterns → Analyze and state the pattern, don't suggest unrelated features
- When asked about trends → Identify the trend (increasing/decreasing/stable)
- NEVER ignore tool results or change the subject
- NEVER suggest features/reminders unless asked
- Answer factual questions with facts, not suggestions

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
    """Determine if agent should continue calling tools based on state."""
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
    """Convert conversation history to LangChain messages with current message."""
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
    """Extract tool calls from message history for response formatting."""
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
    """Extract final response text from message history."""
    if not messages:
        return "No response generated."

    last_message = messages[-1]

    if isinstance(last_message, AIMessage):
        return last_message.content
    else:
        return str(last_message)


def build_error_response(error: Exception, agent_type: str) -> dict[str, Any]:
    """Build standardized error response dict for agents."""
    logger.error(f"{agent_type} chat failed: {error}", exc_info=True)
    return {
        "response": "I encountered an error processing your request. Please try again.",
        "error": str(error),
        "type": agent_type,
        "tools_used": [],
        "tool_calls_made": 0,
    }


def build_tool_error_response(error: Exception, tool_name: str) -> dict[str, Any]:
    """Build standardized error response dict for tools."""
    logger.error(f"Tool {tool_name} failed: {error}", exc_info=True)
    return {
        "error": f"Failed to {tool_name.replace('_', ' ')}: {str(error)}",
        "error_type": type(error).__name__,
        "results": [],
    }
