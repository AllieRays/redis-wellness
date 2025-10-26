"""
Intent Router - Pre-processing to detect goal-setting vs data queries.

Bypasses tool calling for simple goal-setting statements to avoid
LLM over-eagerness with tool calls.
"""

import logging
import re

logger = logging.getLogger(__name__)

# Goal-setting patterns (case-insensitive)
GOAL_SETTING_PATTERNS = [
    r"^my goal is\b",
    r"^i want to\b",
    r"^i plan to\b",
    r"^i'm trying to\b",
    r"^i am trying to\b",
    r"^set a goal\b",
    r"^my target is\b",
    r"^i'd like to\b",
    r"^i would like to\b",
    r"^i need to\b",
]

# Goal retrieval patterns (case-insensitive)
GOAL_RETRIEVAL_PATTERNS = [
    r"^what is my goal",
    r"^what's my goal",
    r"^what are my goals",
    r"^tell me my goal",
    r"^remind me of my goal",
    r"^my goal$",
]


def is_goal_setting_statement(message: str) -> bool:
    """
    Detect if a message is a goal-setting statement.

    Args:
        message: User message to analyze

    Returns:
        True if message is goal-setting, False otherwise

    Examples:
        >>> is_goal_setting_statement("my goal is to never skip leg day")
        True
        >>> is_goal_setting_statement("what is my goal?")
        False
        >>> is_goal_setting_statement("am I meeting my goal?")
        False
    """
    message_lower = message.strip().lower()

    for pattern in GOAL_SETTING_PATTERNS:
        if re.match(pattern, message_lower):
            logger.info(f"🎯 Detected goal-setting statement: '{message[:50]}...'")
            return True

    return False


def is_goal_retrieval_question(message: str) -> bool:
    """
    Detect if a message is asking about their goal.

    Args:
        message: User message to analyze

    Returns:
        True if message is goal retrieval, False otherwise

    Examples:
        >>> is_goal_retrieval_question("what is my goal")
        True
        >>> is_goal_retrieval_question("my goal is to exercise")
        False
    """
    message_lower = message.strip().lower().rstrip("?").rstrip(".")

    for pattern in GOAL_RETRIEVAL_PATTERNS:
        if re.match(pattern, message_lower):
            logger.info(f"🔍 Detected goal retrieval question: '{message[:50]}...'")
            return True

    return False


def extract_goal_from_statement(message: str) -> str:
    """
    Extract the goal description from a goal-setting statement.

    Args:
        message: Goal-setting statement

    Returns:
        The goal description

    Examples:
        >>> extract_goal_from_statement("my goal is to never skip leg day")
        "to never skip leg day"
        >>> extract_goal_from_statement("I want to run 5k every week")
        "to run 5k every week"
    """
    message_lower = message.strip().lower()

    # Try to extract after the pattern
    for pattern in GOAL_SETTING_PATTERNS:
        match = re.match(pattern, message_lower)
        if match:
            # Get everything after the pattern
            goal = message[match.end() :].strip()
            return goal

    # Fallback: return the whole message
    return message


async def retrieve_latest_goal(user_id: str = "wellness_user") -> str | None:
    """
    Retrieve the most recent goal from Redis episodic memory.

    Args:
        user_id: User identifier

    Returns:
        Goal text if found, None otherwise
    """
    try:
        from ..services.episodic_memory_manager import get_episodic_memory

        memory_manager = get_episodic_memory()

        result = await memory_manager.retrieve_goals(
            user_id=user_id,
            query="goal",
            top_k=1,
        )

        if result.get("hits", 0) > 0 and result.get("context"):
            return result["context"]
        return None
    except Exception as e:
        logger.error(f"❌ Failed to retrieve goal: {e}")
        return None


async def should_bypass_tools(message: str) -> tuple[bool, str | None, str | None]:
    """
    Determine if we should bypass tool calling and return a direct response.

    Args:
        message: User message

    Returns:
        Tuple of (should_bypass, direct_response, intent)
        - should_bypass: True if tools should be skipped
        - direct_response: Pre-formatted response if bypass is True, None otherwise
        - intent: "goal_setting", "goal_retrieval", or None

    Examples:
        >>> await should_bypass_tools("my goal is to never skip leg day")
        (True, "Got it! I've saved your goal...", "goal_setting")
        >>> await should_bypass_tools("what is my goal?")
        (True, "Your goal is: ...", "goal_retrieval")
    """
    logger.info(f"🔍 Intent router checking message: '{message[:50]}...'")
    if is_goal_setting_statement(message):
        goal = extract_goal_from_statement(message)
        response = (
            f"Got it! I've saved your goal: {goal}. "
            "I'll help you track your progress toward this goal."
        )
        logger.info(f"✅ Bypassing tools for goal-setting: '{goal[:50]}...'")
        return True, response, "goal_setting"

    if is_goal_retrieval_question(message):
        goal_text = await retrieve_latest_goal()
        if goal_text:
            response = f"Your goal: {goal_text}"
            logger.info(f"✅ Bypassing tools for goal retrieval: '{goal_text[:50]}...'")
            return True, response, "goal_retrieval"
        else:
            response = "You haven't set a goal yet. Try saying 'my goal is...'"
            logger.info("ℹ️ No goal found, returning empty state message")
            return True, response, "goal_retrieval"

    return False, None, None


def chat_with_conditional_tools(
    message: str,
    llm_callable,
    tools: list | None = None,
) -> dict:
    """
    Wrapper around LLM chat that conditionally provides tools based on intent.

    If message is goal-setting, bypass tools entirely and return acknowledgment.
    Otherwise, proceed with normal tool-enabled chat.

    Args:
        message: User message
        llm_callable: Function to call LLM (should accept tools parameter)
        tools: List of available tools

    Returns:
        Dict with response and metadata

    Example:
        >>> def my_llm(message, tools=None):
        ...     # LLM implementation
        ...     return {"response": "..."}
        >>> result = chat_with_conditional_tools(
        ...     "my goal is to exercise daily",
        ...     my_llm,
        ...     tools=[...]
        ... )
        >>> result["response"]
        "Got it! I've saved your goal: to exercise daily..."
    """
    # Check if we should bypass tools
    should_bypass, direct_response = should_bypass_tools(message)

    if should_bypass:
        return {
            "response": direct_response,
            "tools_used": [],
            "tool_calls_made": 0,
            "bypassed_tools": True,
            "intent": "goal_setting",
        }

    # Normal flow with tools
    logger.info(f"🔧 Proceeding with tools for message: '{message[:50]}...'")
    result = llm_callable(message, tools=tools)
    result["bypassed_tools"] = False
    result["intent"] = "query"
    return result
