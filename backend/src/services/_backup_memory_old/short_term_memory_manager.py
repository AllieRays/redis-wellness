"""
Short-Term Memory Manager - Conversation history storage.

Provides:
- Conversation history (Redis LIST)
- Token-aware context retrieval
- Session management
- 7-month TTL

Single-User Mode:
- This is a single-user application (utils.user_config.get_user_id())
- All operations are for the configured user

Architecture:
- Storage: Redis LIST (health_chat_session:{session_id})
- TTL: 7 months (automatic cleanup)
- Token management: Automatic trimming to stay within LLM context window

Usage:
- Use memory_coordinator.py for complete memory orchestration (episodic, procedural, semantic, short-term)
- Use this directly only when you need conversation history without full memory context
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from ..config import get_settings
from ..utils.redis_keys import RedisKeys
from ..utils.token_manager import get_token_manager
from ..utils.user_config import validate_user_context
from .redis_connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class ShortTermMemoryManager:
    """
    Short-term memory manager for conversation history.

    Manages:
    - Recent conversation messages (Redis LIST)
    - Token-aware context retrieval
    - Session clearing

    This provides ONLY short-term memory.
    For complete memory orchestration, use memory_coordinator.py which includes:
    - Short-term (this)
    - Episodic (user preferences/goals)
    - Procedural (learned tool sequences)
    - Semantic (general health knowledge)
    """

    def __init__(self) -> None:
        """Initialize memory manager with embedding model and Redis."""
        self.settings = get_settings()
        self.redis_manager = RedisConnectionManager()

        # Initialize token manager for context window management
        self.token_manager = get_token_manager()

        # TTL for memories (7 months in seconds)
        self.memory_ttl = self.settings.redis_session_ttl_seconds

        logger.info(
            "ShortTermMemoryManager initialized. "
            "For full memory orchestration, use memory_coordinator.py"
        )

    # ========== SHORT-TERM MEMORY ==========

    async def get_short_term_context(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> str | None:
        """
        Get short-term conversation context.

        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Number of recent messages to include

        Returns:
            Formatted string with recent conversation or None
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Validate user_id
                validate_user_context(user_id)
                # Use consistent session key from RedisKeys utility
                session_key = RedisKeys.chat_session(session_id)

                # Get recent messages
                messages = redis_client.lrange(session_key, 0, limit - 1)

                if not messages:
                    return None

                # Format as context
                context_lines = ["Recent conversation:"]

                for msg_json in reversed(messages):  # Chronological order
                    try:
                        msg_data = json.loads(msg_json)
                        role = msg_data.get("role", "unknown")
                        content = msg_data.get("content", "")

                        # Truncate long messages
                        if len(content) > 200:
                            content = content[:200] + "..."

                        context_lines.append(f"{role.capitalize()}: {content}")

                    except json.JSONDecodeError:
                        continue

                return "\n".join(context_lines) if len(context_lines) > 1 else None

        except Exception as e:
            logger.error(f"Short-term memory retrieval failed: {e}")
            return None

    async def store_short_term_message(
        self, user_id: str, session_id: str, role: str, content: str
    ) -> bool:
        """
        Store a message in short-term conversation history.

        Args:
            user_id: User identifier
            session_id: Session identifier
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            True if successful, False otherwise
        """
        try:
            import uuid

            with self.redis_manager.get_connection() as redis_client:
                # Validate user_id
                validate_user_context(user_id)
                # Use consistent session key from RedisKeys utility
                session_key = RedisKeys.chat_session(session_id)

                message_data = {
                    "id": str(uuid.uuid4()),
                    "role": role,
                    "content": content,
                    "timestamp": datetime.now(UTC).isoformat(),
                }

                # Store in Redis LIST (prepend for newest-first)
                redis_client.lpush(session_key, json.dumps(message_data))

                # Set TTL for automatic cleanup
                redis_client.expire(session_key, self.memory_ttl)

                logger.debug(f"Stored {role} message in session {session_id}")
                return True

        except Exception as e:
            logger.error(f"Short-term message storage failed: {e}")
            return False

    async def get_short_term_context_token_aware(
        self, user_id: str, session_id: str, limit: int = 10
    ) -> tuple[str | None, dict[str, Any]]:
        """
        Get short-term context with automatic trimming based on token limits.

        Retrieves recent messages and trims them if they exceed the token threshold,
        ensuring the LLM's context window is never exceeded.

        Args:
            user_id: User identifier
            session_id: Session identifier
            limit: Initial number of recent messages to include

        Returns:
            Tuple of (formatted_context_string, usage_stats_dict)
            Usage stats includes: message_count, token_count, usage_percent, is_over_threshold
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                session_key = RedisKeys.chat_session(session_id)

                # Get recent messages
                raw_messages = redis_client.lrange(session_key, 0, limit - 1)

                if not raw_messages:
                    return None, {"message_count": 0, "token_count": 0}

                # Parse messages
                messages = []
                for msg_json in reversed(
                    raw_messages
                ):  # Reverse for chronological order
                    try:
                        msg_data = json.loads(msg_json)
                        messages.append(msg_data)
                    except json.JSONDecodeError:
                        continue

                # Check and trim if needed
                if messages:
                    (
                        trimmed_messages,
                        original_tokens,
                        trimmed_tokens,
                    ) = self.token_manager.trim_messages(messages)

                    # Format trimmed context
                    context_lines = ["Recent conversation:"]

                    for msg in trimmed_messages:
                        role = msg.get("role", "unknown")
                        content = msg.get("content", "")

                        # Truncate long messages for display
                        if len(content) > 200:
                            content = content[:200] + "..."

                        context_lines.append(f"{role.capitalize()}: {content}")

                    # Get usage statistics
                    usage_stats = self.token_manager.get_usage_stats(trimmed_messages)

                    context_str = (
                        "\n".join(context_lines) if len(context_lines) > 1 else None
                    )
                    return context_str, usage_stats

                return None, {"message_count": 0, "token_count": 0}

        except Exception as e:
            logger.error(f"Token-aware context retrieval failed: {e}")
            return None, {"error": str(e)}

    async def get_session_history_only(
        self, session_id: str, limit: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get conversation history for CURRENT SESSION ONLY.

        This retrieves short-term memory without cross-session semantic search.
        Use for queries like "What was the first thing I asked?"

        Args:
            session_id: Session identifier
            limit: Number of recent messages

        Returns:
            List of message dicts with role, content, timestamp
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                session_key = RedisKeys.chat_session(session_id)
                messages = redis_client.lrange(session_key, 0, limit - 1)

                if not messages:
                    return []

                # Parse and return in chronological order
                parsed = []
                for msg_json in reversed(messages):
                    try:
                        msg_data = json.loads(msg_json)
                        parsed.append(
                            {
                                "role": msg_data.get("role"),
                                "content": msg_data.get("content"),
                                "timestamp": msg_data.get("timestamp"),
                            }
                        )
                    except json.JSONDecodeError:
                        continue

                return parsed
        except Exception as e:
            logger.error(f"Session history retrieval failed: {e}")
            return []

    async def clear_factual_memory(self, user_id: str) -> dict[str, int]:
        """
        Clear factual memory through memory coordinator.

        This is a convenience wrapper. For full control, use memory_coordinator directly.
        """
        from .memory_coordinator import get_memory_coordinator

        coordinator = get_memory_coordinator()
        results = await coordinator.clear_user_memories(
            clear_episodic=True,
            clear_procedural=False,
            clear_semantic=False,
        )
        episodic_result = results.get("episodic", {})
        deleted_count = episodic_result.get("deleted_count", 0)
        return {"deleted_count": deleted_count, "user_id": user_id}

    async def clear_session_memory(self, session_id: str) -> bool:
        """
        Clear all memories for a session.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Clear short-term
                session_key = RedisKeys.chat_session(session_id)
                redis_client.delete(session_key)

                # Clear semantic memories (scan and delete)
                pattern = RedisKeys.semantic_pattern(session_id)
                cursor = 0

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    if keys:
                        redis_client.delete(*keys)

                    if cursor == 0:
                        break

            logger.info(f"Cleared memories for session: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Memory clearing failed: {e}")
            return False

    async def get_memory_stats(self, user_id: str, session_id: str) -> dict[str, Any]:
        """
        Get statistics about user's memory.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            Dict with memory statistics
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Short-term stats
                session_key = RedisKeys.chat_session(session_id)
                short_term_count = redis_client.llen(session_key)
                short_term_ttl = redis_client.ttl(session_key)

                # Long-term stats (approximate via scan)
                pattern = RedisKeys.semantic_pattern(user_id)
                cursor = 0
                long_term_count = 0

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                    long_term_count += len(keys)

                    if cursor == 0:
                        break

                return {
                    "short_term": {
                        "message_count": short_term_count,
                        "ttl_seconds": short_term_ttl if short_term_ttl > 0 else None,
                    },
                    "long_term": {
                        "memory_count": long_term_count,
                        "semantic_search_enabled": True,  # Fixed: removed reference to non-existent self.semantic_index
                    },
                    "user_id": user_id,
                    "session_id": session_id,
                }

        except Exception as e:
            logger.error(f"Memory stats retrieval failed: {e}")
            return {"error": str(e)}


# Global short-term memory manager instance
_short_term_memory_manager: ShortTermMemoryManager | None = None


def get_short_term_memory_manager() -> ShortTermMemoryManager:
    """
    Get or create the global short-term memory manager.

    Returns:
        ShortTermMemoryManager instance
    """
    global _short_term_memory_manager

    if _short_term_memory_manager is None:
        _short_term_memory_manager = ShortTermMemoryManager()

    return _short_term_memory_manager


# Alias for convenience
get_memory_manager = get_short_term_memory_manager
