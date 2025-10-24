"""
Simple Pronoun Resolver.

Tracks the last topic discussed and resolves pronouns like "that", "it".
Fixes Bug #2: Follow-up questions failing due to pronoun resolution.
"""

import json
import logging

logger = logging.getLogger(__name__)


class PronounResolver:
    """
    Simple pronoun resolution based on conversation history.

    Strategy:
    - Track last health metric/topic mentioned
    - Resolve "that"/"it" to last topic
    - Store in Redis with session TTL
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    def _get_context_key(self, session_id: str) -> str:
        """Get Redis key for conversation context."""
        return f"pronoun_context:{session_id}"

    def extract_topic_from_query(self, query: str) -> str | None:
        """
        Extract health topic from query.

        Returns human-readable topic name.
        """
        import re

        query_lower = query.lower()

        # Health metrics
        if "bmi" in query_lower or "body mass index" in query_lower:
            return "BMI"
        elif re.search(r"\b(weigh|weighed|weighing|wt)\b", query_lower) or (
            "weight" in query_lower and "body" not in query_lower
        ):
            return "weight"
        elif "heart rate" in query_lower:
            return "heart rate"
        elif "workout" in query_lower or "exercise" in query_lower:
            return "workouts"
        elif re.search(r"\b(step|steps|stepping|walked|walking|walk)\b", query_lower):
            return "steps"
        elif re.search(r"\b(calor\w*|kcal|cal)\b", query_lower) and re.search(
            r"\b(burn|burned|burning|active)\b", query_lower
        ):
            return "calories burned"

        return None

    def extract_topic_from_response(
        self, response: str, tools_used: list
    ) -> str | None:
        """
        Extract topic from response and tool usage.

        Args:
            response: Assistant's response text
            tools_used: List of tool names (strings) or tool dicts (for backward compatibility)

        Returns:
            Topic name or None
        """
        # Check tool calls
        for tool in tools_used:
            # Handle both list[str] and list[dict] for backward compatibility
            tool_name = tool.get("name", "") if isinstance(tool, dict) else str(tool)

            if "workout" in tool_name.lower():
                return "workouts"
            elif "metric" in tool_name.lower() and isinstance(tool, dict):
                # For dict format, try to extract metric from args
                args = tool.get("args", {})
                metric_types = args.get("metric_types", [])
                if metric_types:
                    first_metric = metric_types[0]
                    if "BodyMassIndex" in first_metric:
                        return "BMI"
                    elif "BodyMass" in first_metric:
                        return "weight"
                    elif "HeartRate" in first_metric:
                        return "heart rate"

        return None

    def update_context(
        self,
        session_id: str,
        query: str,
        response: str,
        tools_used: list,
        ttl: int = 604800,
    ):
        """
        Update conversation context after each exchange.

        Args:
            session_id: Session ID
            query: User's query
            response: Assistant's response
            tools_used: Tools that were called
            ttl: TTL in seconds (default: 7 days)
        """
        try:
            # Extract topic from query or response
            topic = self.extract_topic_from_query(query)
            if not topic:
                topic = self.extract_topic_from_response(response, tools_used)

            if topic:
                context_data = {
                    "last_topic": topic,
                    "last_query": query[:200],  # Store truncated for reference
                }

                key = self._get_context_key(session_id)
                self.redis.setex(key, ttl, json.dumps(context_data))
                logger.debug(f"Updated pronoun context: last_topic={topic}")

        except Exception as e:
            logger.warning(f"Failed to update pronoun context: {e}")

    def resolve_pronouns(self, session_id: str, query: str) -> str:
        """
        Resolve pronouns in query to explicit references.

        Args:
            session_id: Session ID
            query: User's query

        Returns:
            Query with pronouns resolved (or original if no resolution needed)
        """
        try:
            query_lower = query.lower()

            # Check if query contains pronouns
            has_pronoun = any(
                pattern in query_lower
                for pattern in [
                    "is that",
                    "about that",
                    "tell me more about it",
                    " it ",
                    "is it",
                ]
            )

            if not has_pronoun:
                return query

            # Get last topic from context
            key = self._get_context_key(session_id)
            context_json = self.redis.get(key)

            if not context_json:
                return query  # No context available

            context = json.loads(context_json)
            last_topic = context.get("last_topic")

            if not last_topic:
                return query

            # Replace pronouns with topic
            resolved = query

            # "Is that" -> "Is BMI" (or whatever topic)
            if query_lower.startswith("is that "):
                resolved = query.replace("Is that ", f"Is {last_topic} ", 1)
                resolved = resolved.replace("is that ", f"is {last_topic} ", 1)

            # "About that" -> "About BMI"
            if "about that" in query_lower:
                resolved = query.replace("about that", f"about {last_topic}")
                resolved = resolved.replace("About that", f"About {last_topic}")

            # "Tell me more about it" -> "Tell me more about BMI"
            if "about it" in query_lower:
                resolved = query.replace("about it", f"about {last_topic}")
                resolved = resolved.replace("About it", f"About {last_topic}")

            # " it " -> " BMI " (careful with this one)
            if " it " in query_lower and resolved == query:
                resolved = query.replace(" it ", f" {last_topic} ")
                resolved = resolved.replace(" It ", f" {last_topic} ")

            if resolved != query:
                logger.info(f"Resolved pronoun: '{query}' -> '{resolved}'")

            return resolved

        except Exception as e:
            logger.warning(f"Pronoun resolution failed: {e}")
            return query  # Return original on error


def get_pronoun_resolver(redis_client) -> PronounResolver:
    """Create pronoun resolver instance."""
    return PronounResolver(redis_client)
