"""Centralized Redis key generation for consistent naming across services."""


class RedisKeys:
    """Redis key generation organized by domain (health, workout, memory, cache)."""

    # ========== HEALTH DATA KEYS ==========

    @staticmethod
    def health_data(user_id: str) -> str:
        """
        Main health data collection key.

        Stores: Complete parsed health data (permanent storage)
        Format: health:user:{user_id}:data
        TTL: None (permanent)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.health_data(get_user_id())
            # Returns: "health:user:wellness_user:data"
        """
        return f"health:user:{user_id}:data"

    @staticmethod
    def health_metric(user_id: str, metric_type: str) -> str:
        """
        Health metric index key for fast queries.

        Stores: Metric-specific aggregations (e.g., heart_rate, steps)
        Format: health:user:{user_id}:metric:{metric_type}
        TTL: 210 days (7 months)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.health_metric(get_user_id(), "heart_rate")
            # Returns: "health:user:wellness_user:metric:heart_rate"
        """
        return f"health:user:{user_id}:metric:{metric_type}"

    @staticmethod
    def health_context(user_id: str) -> str:
        """
        Health conversation context key.

        Stores: Health-aware conversation context
        Format: health:user:{user_id}:context
        TTL: None (permanent)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.health_context(get_user_id())
            # Returns: "health:user:wellness_user:context"
        """
        return f"health:user:{user_id}:context"

    @staticmethod
    def health_recent_insights(user_id: str) -> str:
        """
        Recent health insights key.

        Stores: Record count, categories, date range
        Format: health:user:{user_id}:recent_insights
        TTL: 210 days (7 months)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.health_recent_insights(get_user_id())
            # Returns: "health:user:wellness_user:recent_insights"
        """
        return f"health:user:{user_id}:recent_insights"

    @staticmethod
    def health_pattern(user_id: str) -> str:
        """
        Pattern for all health keys for a user (scanning/deletion).

        Format: health:user:{user_id}:*

        Example:
            from ..utils.user_config import get_user_id
            pattern = RedisKeys.health_pattern(get_user_id())
            keys = redis.keys(pattern)
        """
        return f"health:user:{user_id}:*"

    # ========== WORKOUT KEYS ==========

    @staticmethod
    def workout_days(user_id: str) -> str:
        """
        Workout count by day of week (Redis Hash).

        Stores: day_of_week → count mapping
        Format: user:{user_id}:workout:days
        TTL: 210 days (7 months)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.workout_days(get_user_id())
            # Returns: "user:wellness_user:workout:days"
        """
        return f"user:{user_id}:workout:days"

    @staticmethod
    def workout_by_date(user_id: str) -> str:
        """
        Workout index by date (Redis Sorted Set).

        Stores: workout_id → timestamp mapping for range queries
        Format: user:{user_id}:workout:by_date
        TTL: 210 days (7 months)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.workout_by_date(get_user_id())
            # Returns: "user:wellness_user:workout:by_date"
        """
        return f"user:{user_id}:workout:by_date"

    @staticmethod
    def workout_detail(user_id: str, workout_id: str) -> str:
        """
        Individual workout details (Redis Hash).

        Stores: date, type, duration, calories, etc.
        Format: user:{user_id}:workout:{workout_id}
        TTL: 210 days (7 months)

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.workout_detail(get_user_id(), "2024-10-15:Running:080000")
            # Returns: "user:wellness_user:workout:2024-10-15:Running:080000"
        """
        return f"user:{user_id}:workout:{workout_id}"

    # ========== MEMORY KEYS ==========

    @staticmethod
    def chat_session(session_id: str) -> str:
        """
        Chat session history (Redis LIST).

        Stores: Conversation messages in chronological order
        Format: health_chat_session:{session_id}
        TTL: 7 months (18144000 seconds)

        Example:
            key = RedisKeys.chat_session("demo")
            # Returns: "health_chat_session:demo"
        """
        return f"health_chat_session:{session_id}"

    @staticmethod
    def episodic_memory(user_id: str, event_type: str, timestamp: int) -> str:
        """
        Episodic memory (user-specific events).

        Stores: User preferences, goals, health events, interactions
        Format: episodic:{user_id}:{event_type}:{timestamp}
        TTL: 7 months

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.episodic_memory(get_user_id(), "preference", 1729737600)
            # Returns: "episodic:wellness_user:preference:1729737600"
        """
        return f"episodic:{user_id}:{event_type}:{timestamp}"

    @staticmethod
    def procedural_memory(user_id: str, query_hash: str) -> str:
        """
        Procedural memory (learned tool sequences).

        Stores: Tool-calling patterns, execution stats, success scores
        Format: procedure:{user_id}:{query_hash}
        TTL: 7 months

        Example:
            from ..utils.user_config import get_user_id
            key = RedisKeys.procedural_memory(get_user_id(), "a1b2c3d4")
            # Returns: "procedure:wellness_user:a1b2c3d4"
        """
        return f"procedure:{user_id}:{query_hash}"

    @staticmethod
    def semantic_memory(category: str, fact_type: str, timestamp: int) -> str:
        """
        Semantic memory (general health knowledge).

        Stores: Health facts, definitions, relationships, guidelines
        Format: semantic:{category}:{fact_type}:{timestamp}
        TTL: 7 months

        Example:
            key = RedisKeys.semantic_memory("cardio", "definition", 1729737600)
            # Returns: "semantic:cardio:definition:1729737600"
        """
        return f"semantic:{category}:{fact_type}:{timestamp}"

    @staticmethod
    def semantic_pattern(user_id: str) -> str:
        """
        Pattern for all semantic memory keys for a user (scanning/deletion).

        Format: memory:semantic:{user_id}:*

        Example:
            from ..utils.user_config import get_user_id
            pattern = RedisKeys.semantic_pattern(get_user_id())
            keys = redis.keys(pattern)
        """
        return f"memory:semantic:{user_id}:*"

    # ========== CACHE KEYS ==========

    @staticmethod
    def embedding_cache(query_hash: str) -> str:
        """
        Embedding cache key.

        Stores: Cached embedding vectors
        Format: embedding_cache:{query_hash}
        TTL: 1 hour (configurable)

        Example:
            key = RedisKeys.embedding_cache("a1b2c3d4e5f6...")
            # Returns: "embedding_cache:a1b2c3d4e5f6..."
        """
        return f"embedding_cache:{query_hash}"

    # ========== PATTERN KEYS (for scanning/deletion) ==========

    @staticmethod
    def all_user_data(user_id: str) -> str:
        """
        Pattern for ALL user-related keys (health, workouts, memories).

        Format: Multiple patterns (health:user:{user_id}:*, user:{user_id}:*, etc.)

        Note: Use specific patterns instead:
        - RedisKeys.health_pattern(user_id)
        - RedisKeys.workout_pattern(user_id)
        - RedisKeys.memory_pattern(user_id)
        """
        raise NotImplementedError(
            "Use specific patterns: health_pattern(), workout_pattern(), or memory_pattern()"
        )

    @staticmethod
    def workout_pattern(user_id: str) -> str:
        """
        Pattern for all workout keys for a user.

        Format: user:{user_id}:workout:*

        Example:
            from ..utils.user_config import get_user_id
            pattern = RedisKeys.workout_pattern(get_user_id())
            keys = redis.keys(pattern)
        """
        return f"user:{user_id}:workout:*"

    @staticmethod
    def memory_pattern(user_id: str) -> str:
        """
        Pattern for all memory keys for a user (episodic + procedural).

        Format: *:{user_id}:*

        Note: This is a loose pattern. For specific memory types:
        - Episodic: f"episodic:{user_id}:*"
        - Procedural: f"procedure:{user_id}:*"
        - Semantic: Use semantic_pattern()

        Example:
            from ..utils.user_config import get_user_id
            pattern = RedisKeys.memory_pattern(get_user_id())
            keys = redis.keys(pattern)
        """
        return f"*{user_id}*"  # Broad pattern - use with caution

    # ========== REDIS INDEX NAMES ==========

    # These are used by RedisVL for vector search indexes

    SEMANTIC_KNOWLEDGE_INDEX = "semantic_knowledge_idx"
    """RedisVL index name for semantic memory (general health knowledge)."""

    EPISODIC_MEMORY_INDEX = "episodic_memory_idx"
    """RedisVL index name for episodic memory (user-specific events)."""

    # ========== KEY PREFIXES ==========

    # These are used by RedisVL schema definitions

    SEMANTIC_PREFIX = "semantic:"
    """RedisVL prefix for semantic memory keys."""

    EPISODIC_PREFIX = "episodic:"
    """RedisVL prefix for episodic memory keys."""

    HEALTH_PREFIX = "health:user:"
    """Prefix for health data keys."""

    WORKOUT_PREFIX = "user:"
    """Prefix for workout keys."""

    EMBEDDING_CACHE_PREFIX = "embedding_cache:"
    """Prefix for embedding cache keys."""


# ========== CONVENIENCE FUNCTIONS ==========


def generate_workout_id(date: str, workout_type: str, start_time: str = "") -> str:
    """
    Generate unique workout ID for indexing.

    Args:
        date: Workout date (YYYY-MM-DD)
        workout_type: Type of workout (e.g., "Running", "Cycling")
        start_time: Optional start time for uniqueness (HHMMSS)

    Returns:
        Unique workout ID

    Example:
        workout_id = generate_workout_id("2024-10-15", "Running", "080000")
        # Returns: "2024-10-15:Running:080000"
    """
    if start_time:
        return f"{date}:{workout_type}:{start_time}"
    return f"{date}:{workout_type}"


def parse_workout_id(workout_id: str) -> dict[str, str]:
    """
    Parse workout ID back into components.

    Args:
        workout_id: Workout ID (e.g., "2024-10-15:Running:080000")

    Returns:
        Dict with date, workout_type, and optional start_time

    Example:
        parts = parse_workout_id("2024-10-15:Running:080000")
        # Returns: {"date": "2024-10-15", "workout_type": "Running", "start_time": "080000"}
    """
    parts = workout_id.split(":")
    if len(parts) == 3:
        return {"date": parts[0], "workout_type": parts[1], "start_time": parts[2]}
    return {"date": parts[0], "workout_type": parts[1], "start_time": ""}
