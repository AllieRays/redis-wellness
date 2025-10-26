"""
Shared intent bypass handler for both stateless and stateful agents.

Handles goal-setting and goal-retrieval intents that should bypass the tool loop.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def handle_intent_bypass(
    message: str,
    user_id: str,
    is_stateful: bool = False,
) -> dict[str, Any] | None:
    """
    Check if message should bypass tool loop and return direct response.

    Args:
        message: User's message
        user_id: User identifier
        is_stateful: Whether agent has memory storage capability

    Returns:
        Response dict if intent should bypass, None otherwise
    """
    from .intent_router import extract_goal_from_statement, should_bypass_tools

    should_bypass, direct_response, intent = await should_bypass_tools(message)

    if not should_bypass:
        return None

    # Handle goal-setting intent
    if intent == "goal_setting":
        logger.info(
            f"✅ {'Stateful' if is_stateful else 'Stateless'}: "
            f"Bypassed tools for goal-setting"
        )

        goal_text = extract_goal_from_statement(message)

        # Stateful agent stores goal, stateless just acknowledges
        if is_stateful:
            await _store_goal_in_redis(user_id, goal_text)
            # Use direct_response from intent_router
        else:
            direct_response = f"Got it! You mentioned your goal: {goal_text}."
            logger.info("(NO storage - stateless)")

        token_stats = _calculate_token_stats(message, direct_response)

        return {
            "response": direct_response,
            "tools_used": [],
            "tool_calls_made": 0,
            "memory_stats": {
                "semantic_hits": 0,
                "goals_stored": 1 if is_stateful else 0,
                "procedural_patterns_used": 0,
                "memory_type": "none",
                "memory_types": [],
                "short_term_available": False,
            },
            "token_stats": token_stats,
            "validation": {
                "valid": True,
                "score": 1.0,
                "hallucinations_detected": 0,
                "numbers_validated": 0,
                "total_numbers": 0,
            },
        }

    # Handle goal-retrieval intent
    if intent == "goal_retrieval":
        logger.info(
            f"✅ {'Stateful' if is_stateful else 'Stateless'}: "
            f"Bypassed tools for goal retrieval"
        )

        # Stateless has no memory to retrieve
        if not is_stateful:
            direct_response = (
                "I don't have any information about your goals. "
                "Would you like to share your goal with me?"
            )

        token_stats = _calculate_token_stats(message, direct_response)

        return {
            "response": direct_response,
            "tools_used": [],
            "tool_calls_made": 0,
            "memory_stats": {
                "semantic_hits": 0,
                "goals_stored": 0,
                "procedural_patterns_used": 0,
                "memory_type": "none",
                "memory_types": [],
                "short_term_available": False,
            },
            "token_stats": token_stats,
            "validation": {
                "valid": True,
                "score": 1.0,
                "hallucinations_detected": 0,
                "numbers_validated": 0,
                "total_numbers": 0,
            },
        }

    return None


async def _store_goal_in_redis(user_id: str, goal_text: str) -> None:
    """Store goal in Redis episodic memory (stateful agent only)."""
    try:
        import json

        import numpy as np

        from ..config import get_settings
        from ..services.embedding_service import get_embedding_service
        from ..services.episodic_memory_manager import get_episodic_memory
        from ..services.redis_connection import get_redis_manager
        from .redis_keys import RedisKeys
        from .time_utils import get_utc_timestamp

        # Ensure episodic memory is initialized
        get_episodic_memory()

        redis_manager = get_redis_manager()
        timestamp = get_utc_timestamp()
        memory_key = RedisKeys.episodic_memory(user_id, "goal", timestamp)

        # Generate embedding for semantic search
        embedding_service = get_embedding_service()
        embedding = await embedding_service.generate_embedding(
            f"User's goal: {goal_text}"
        )

        if embedding:
            memory_data = {
                "user_id": user_id,
                "event_type": "goal",
                "timestamp": timestamp,
                "description": f"User's goal: {goal_text}",
                "metadata": json.dumps({"goal_text": goal_text}),
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }

            with redis_manager.get_connection() as redis_client:
                redis_client.hset(memory_key, mapping=memory_data)
                # Set TTL (7 months)
                settings = get_settings()
                redis_client.expire(memory_key, settings.redis_session_ttl_seconds)

            logger.info(f"💾 Stored goal in Redis: '{goal_text}'")

    except Exception as e:
        logger.error(f"❌ Failed to store goal: {e}", exc_info=True)


def _calculate_token_stats(message: str, response: str) -> dict[str, Any]:
    """Calculate token statistics for a message/response pair."""
    try:
        from .token_manager import get_token_manager

        token_manager = get_token_manager()
        messages_for_counting = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": response},
        ]
        return token_manager.get_usage_stats(messages_for_counting)
    except Exception as e:
        logger.warning(f"Could not calculate token stats: {e}")
        return {}
