"""
Goal Management Tools - Fast goal storage for LangChain.

Provides a lightweight tool for storing user goals without heavy analysis.
This tool is currently DEPRECATED - goal storage is handled by intent_bypass_handler.
Kept for reference but not included in active toolset.
"""

import json
import logging
import re

from langchain_core.tools import tool
from pydantic import Field

logger = logging.getLogger(__name__)


def _extract_goal_components(goal_description: str) -> dict:
    """
    Extract structured components from goal description.

    Patterns:
    - "reach 150 lbs" → {metric: "weight", value: 150, unit: "lbs"}
    - "run 5 miles" → {metric: "distance", value: 5, unit: "miles"}
    - "never skip leg day" → {goal_text: "never skip leg day"}

    Args:
        goal_description: Natural language goal description

    Returns:
        Dict with extracted components
    """
    goal_lower = goal_description.lower()

    # Weight patterns
    weight_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(lbs?|pounds?|kg|kilograms?)", goal_lower
    )
    if weight_match and any(
        kw in goal_lower for kw in ["weight", "weigh", "reach", "get to"]
    ):
        return {
            "metric": "weight",
            "value": float(weight_match.group(1)),
            "unit": "lbs"
            if "lb" in weight_match.group(2) or "pound" in weight_match.group(2)
            else "kg",
            "goal_text": goal_description,
        }

    # Distance patterns
    distance_match = re.search(r"(\d+(?:\.\d+)?)\s*(miles?|km|kilometers?)", goal_lower)
    if distance_match and any(
        kw in goal_lower for kw in ["run", "walk", "bike", "distance"]
    ):
        return {
            "metric": "distance",
            "value": float(distance_match.group(1)),
            "unit": "mi" if "mile" in distance_match.group(2) else "km",
            "goal_text": goal_description,
        }

    # Steps pattern
    steps_match = re.search(r"(\d+(?:,\d+)?)\s*steps?", goal_lower)
    if steps_match:
        steps_value = steps_match.group(1).replace(",", "")
        return {
            "metric": "steps",
            "value": int(steps_value),
            "unit": "count",
            "goal_text": goal_description,
        }

    # Workout frequency patterns
    if any(kw in goal_lower for kw in ["workout", "exercise", "train"]):
        freq_match = re.search(
            r"(\d+)\s*(times?|days?)(?:\s*(?:per|a)\s*week)?", goal_lower
        )
        if freq_match:
            return {
                "metric": "workout_frequency",
                "value": int(freq_match.group(1)),
                "unit": "per_week",
                "goal_text": goal_description,
            }

    # Fallback: text-only goal
    return {"goal_text": goal_description}


@tool
async def store_user_goal(
    goal_description: str = Field(description="The user's goal in their own words"),
    user_id: str = Field(default="wellness_user", description="User identifier"),
) -> str:
    """
    Store a user's stated goal or intention in episodic memory.

    Use this when the user STATES a goal (not asking a question):
    - "my goal is X" → store_user_goal("X")
    - "I want to X" → store_user_goal("X")
    - "I'm trying to X" → store_user_goal("X")

    This tool extracts structured data when possible and stores it for semantic search.

    Args:
        goal_description: What the user wants to achieve (clean text, no preamble)
        user_id: User identifier

    Returns:
        JSON string with storage status

    Example:
        User: "my goal is to reach 150 lbs"
        Call: store_user_goal(goal_description="reach 150 lbs")
        Returns: '{"status": "success", "goal": "reach 150 lbs", "stored": true}'
    """
    if not goal_description or not goal_description.strip():
        return json.dumps(
            {"status": "error", "message": "Goal description is empty", "stored": False}
        )

    try:
        logger.info(f"💾 Goal storage: user={user_id}, goal='{goal_description[:60]}'")

        # Extract structured components
        goal_data = _extract_goal_components(goal_description)
        logger.info(f"   Extracted: {goal_data}")

        # Store in episodic memory
        from ...services.episodic_memory_manager import get_episodic_memory

        memory = get_episodic_memory()

        if not memory:
            logger.error("Episodic memory not initialized")
            return json.dumps(
                {
                    "status": "error",
                    "message": "Memory system unavailable",
                    "stored": False,
                }
            )

        # Store as structured goal if we have metric/value, otherwise text-only
        if "metric" in goal_data and "value" in goal_data:
            success = await memory.store_goal(
                user_id=user_id,
                metric=goal_data["metric"],
                value=goal_data["value"],
                unit=goal_data.get("unit", "text"),
            )
        else:
            # Text-only goal: store using custom storage method
            import numpy as np

            from ...config import get_settings
            from ...services.embedding_service import get_embedding_service
            from ...services.redis_connection import get_redis_manager
            from ...utils.redis_keys import RedisKeys
            from ...utils.time_utils import get_utc_timestamp

            timestamp = get_utc_timestamp()
            memory_key = RedisKeys.episodic_memory(user_id, "goal", timestamp)

            embedding_service = get_embedding_service()
            embedding = await embedding_service.generate_embedding(
                f"User's goal: {goal_description}"
            )

            if embedding:
                memory_data = {
                    "user_id": user_id,
                    "event_type": "goal",
                    "timestamp": timestamp,
                    "description": f"User's goal: {goal_description}",
                    "metadata": json.dumps(goal_data),
                    "embedding": np.array(embedding, dtype=np.float32).tobytes(),
                }

                redis_manager = get_redis_manager()
                settings = get_settings()

                with redis_manager.get_connection() as redis_client:
                    redis_client.hset(memory_key, mapping=memory_data)
                    redis_client.expire(memory_key, settings.redis_session_ttl_seconds)

                success = True
            else:
                success = False

        if success:
            logger.info("✅ Goal stored successfully")
            return json.dumps(
                {
                    "status": "success",
                    "goal": goal_description,
                    "stored": True,
                    "message": f"Goal saved: {goal_description}",
                }
            )
        else:
            logger.warning("⚠️ Goal storage failed")
            return json.dumps(
                {
                    "status": "partial",
                    "goal": goal_description,
                    "stored": False,
                    "message": f"I noted your goal ({goal_description}) but couldn't persist it",
                }
            )

    except Exception as e:
        logger.error(f"❌ Goal storage exception: {e}", exc_info=True)
        return json.dumps(
            {
                "status": "error",
                "goal": goal_description,
                "stored": False,
                "message": "Storage error occurred",
                "error": str(e),
            }
        )
