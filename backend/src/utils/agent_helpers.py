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

📊 TOOL SELECTION RULES (Qwen Best Practices):

For COMPARISON queries ("compare", "vs", "versus", "how does that compare"):
- Keywords: "compare", "versus", "vs", "compared to", "difference between"
- ALWAYS use get_health_metrics with aggregations=["sum"] for ANY period you don't have tool data for
- Example: "compare that to April" → Call get_health_metrics(metric_types=["StepCount"], time_period="april", aggregations=["sum"])
- You MAY use conversation history to understand what metric, but you MUST call tools for any period
- NEVER make up numbers for comparisons

For STATISTICS queries ("total", "average", "sum", "how many"):
- Keywords: "total", "sum", "average", "mean", "min", "max", "count"
- ALWAYS use get_health_metrics with aggregations parameter
- Example: "total steps this month" → Call get_health_metrics(metric_types=["StepCount"], time_period="this month", aggregations=["sum"])

🔧 CRITICAL - TOOL CALLING FORMAT:
When calling a tool, return ONLY the tool call with NO additional text.
After receiving tool results, then respond with your analysis text.
Never include both text and tool calls in the same response.

⚠️ TOOL-FIRST POLICY:
- For factual questions about workouts/health data → ALWAYS call health data tools (source of truth)
- NEVER answer workout/metric questions without tool data
- Always verify data through tools before responding
- If tools return no data, respond with "I don't have that data in your Apple Health records"

🎯 GOAL QUESTIONS:
When users ASK about goals, use memory + health tools:
✅ "am I meeting my goal?" → Call get_my_goals first, then check health data
✅ "how am I doing with my goal?" → Retrieve goal first, then analyze progress
✅ "what is my goal?" → Call get_my_goals only

Note: Goal SETTING ("my goal is X") is handled automatically before you see it.

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
❌ WRONG: "When did I work out last?" → Don't use memory, use get_workout_data directly
❌ WRONG: "Did I work out on Friday?" → Don't use memory, use get_workout_data directly
❌ WRONG: "How many workouts this week?" → Don't use memory, use get_workout_data directly

CRITICAL - HEALTH TOOL USAGE EXAMPLES:

EXAMPLE 1 - Recent Workouts:
User: "tell me about my recent workouts"
→ Call: get_workout_data(days_back=30)
→ Wait for results, then respond with summary

EXAMPLE 2 - Specific Date:
User: "did I work out on October 17?"
→ Call: get_workout_data(start_date="2024-10-17", days_back=90)
→ Answer YES or NO with workout details

EXAMPLE 3 - Health Metrics:
User: "what's my weight?"
→ Call: get_health_metrics(metric_types=["BodyMass"], days_back=1)
→ Response: "Your current weight is X lb"

IMPORTANT RULES:
- Specific dates ("October 17", "last Friday") → ALWAYS use days_back=90 or higher
- Recent queries ("recent workouts", "last week") → Use days_back=30
- NEVER use days_back=1 unless user says "today"
- NEVER make up workout data - ALWAYS call tools first
- NEVER respond without calling tools for factual questions

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

🏥 INJURY & RECOVERY GUIDANCE:
When users ask about their injury or recovery, you MUST call tools to get actual data:
- REQUIRED: Use get_workout_progress tool with start_date from injury date
- REQUIRED: Use get_workout_patterns tool to check training consistency
- Focus analysis on injury-relevant metrics (upper body for collarbone, right hip for bone graft)
- Compare current activity to pre-injury levels when data is available
- If they say "yes" or express interest, proceed with tool calls immediately
- NEVER respond about injury/recovery without calling tools first"""
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
