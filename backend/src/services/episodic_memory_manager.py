"""
Episodic Memory Manager - Stores user-specific events and experiences.

Based on CoALA framework (https://arxiv.org/pdf/2309.02427):
"Episodic memory stores specific past events and experiences, like a personal
diary of the AI's interactions."

Examples of Episodic Memories:
- User preferences: "User prefers morning workouts"
- User goals: "User's BMI goal is 22"
- Health events: "User mentioned knee pain on 2024-10-15"
- Past interactions: "User previously asked about heart rate zones"

Storage Strategy:
- RedisVL vector index with event_type filtering
- Prefix: episodic:{user_id}:{event_type}:{timestamp}
- Enables semantic search within specific event categories
"""

import json
import logging
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from redisvl.schema import IndexSchema

from ..config import get_settings
from ..utils.exceptions import MemoryRetrievalError
from ..utils.redis_keys import RedisKeys
from .embedding_service import get_embedding_service
from .redis_connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class EpisodicEventType(str, Enum):
    """Types of episodic memories we track."""

    PREFERENCE = "preference"  # User preferences (e.g., "prefers morning workouts")
    GOAL = "goal"  # User goals (e.g., "target weight: 150 lbs")
    HEALTH_EVENT = "health_event"  # Health-related events (e.g., "mentioned knee pain")
    INTERACTION = "interaction"  # Past interaction patterns (e.g., "frequently asks about heart rate")
    MILESTONE = "milestone"  # Achievements (e.g., "completed first 5K run")


class EpisodicMemoryManager:
    """
    Manages episodic memories: user-specific events, preferences, and experiences.

    Episodic memory is personal and contextual - it remembers:
    - What the user prefers
    - What goals they've set
    - What health events they've mentioned
    - Past interaction patterns

    This is separate from semantic memory (general health knowledge)
    and procedural memory (learned tool sequences).
    """

    def __init__(self) -> None:
        """Initialize episodic memory manager with RedisVL index."""
        self.settings = get_settings()
        self.redis_manager = RedisConnectionManager()

        # Use centralized embedding service
        self.embedding_service = get_embedding_service()

        # Initialize RedisVL index for episodic memory
        self.episodic_index = None
        self._initialize_episodic_index()

        # TTL for episodic memories (7 months, same as other memories)
        self.memory_ttl = self.settings.redis_session_ttl_seconds

        logger.info("EpisodicMemoryManager initialized successfully")

    def _initialize_episodic_index(self) -> None:
        """Initialize RedisVL index for episodic memory with event_type filtering."""
        try:
            schema = IndexSchema.from_dict(
                {
                    "index": {
                        "name": RedisKeys.EPISODIC_MEMORY_INDEX,
                        "prefix": RedisKeys.EPISODIC_PREFIX,
                        "storage_type": "hash",
                    },
                    "fields": [
                        {"name": "user_id", "type": "tag"},
                        {"name": "event_type", "type": "tag"},  # NEW: Filter by type
                        {"name": "timestamp", "type": "numeric"},
                        {"name": "description", "type": "text"},
                        {"name": "context", "type": "text"},
                        {"name": "metadata", "type": "text"},  # JSON string
                        {
                            "name": "embedding",
                            "type": "vector",
                            "attrs": {
                                "dims": 1024,  # mxbai-embed-large dimension
                                "distance_metric": "cosine",
                                "algorithm": "hnsw",
                                "datatype": "float32",
                            },
                        },
                    ],
                }
            )

            self.episodic_index = SearchIndex(schema=schema)

            # Connect to Redis
            redis_url = f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"
            self.episodic_index.connect(redis_url)

            # Create index if it doesn't exist
            try:
                self.episodic_index.create(overwrite=False)
                logger.info("Created episodic memory index")
            except Exception:
                logger.info("Episodic memory index already exists")

        except Exception as e:
            logger.error(f"Failed to initialize episodic index: {e}")
            self.episodic_index = None

    async def store_episodic_event(
        self,
        user_id: str,
        event_type: EpisodicEventType,
        description: str,
        context: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store an episodic memory (user-specific event).

        Args:
            user_id: User identifier
            event_type: Type of episodic event (preference, goal, health_event, etc.)
            description: Brief description of the event
            context: Additional context about the event
            metadata: Additional structured data

        Returns:
            True if successful, False otherwise

        Examples:
            from ..utils.user_config import get_user_id

            await store_episodic_event(
                user_id=get_user_id(),
                event_type=EpisodicEventType.PREFERENCE,
                description="User prefers morning workouts",
                context="Mentioned during conversation about workout scheduling"
            )

            await store_episodic_event(
                user_id=get_user_id(),
                event_type=EpisodicEventType.GOAL,
                description="User's BMI goal is 22",
                context="User expressed desire to reach healthy BMI range",
                metadata={"current_bmi": 25.3, "target_bmi": 22}
            )
        """
        if not self.episodic_index:
            return False

        try:
            # Combine description and context for embedding
            combined_text = f"{description}\n{context}" if context else description

            # Generate embedding using centralized service
            embedding = await self.embedding_service.generate_embedding(combined_text)
            if embedding is None:
                return False

            # Create memory record
            timestamp = int(datetime.now(UTC).timestamp())
            memory_key = RedisKeys.episodic_memory(user_id, event_type.value, timestamp)

            # Store in RedisVL
            with self.redis_manager.get_connection() as redis_client:
                import numpy as np

                memory_data = {
                    "user_id": user_id,
                    "event_type": event_type.value,
                    "timestamp": timestamp,
                    "description": description,
                    "context": context,
                    "metadata": json.dumps(metadata or {}),
                    "embedding": np.array(embedding, dtype=np.float32).tobytes(),
                }

                # Store as hash
                redis_client.hset(memory_key, mapping=memory_data)

                # Set TTL
                redis_client.expire(memory_key, self.memory_ttl)

            logger.info(
                f"Stored episodic memory: {event_type.value} - {description[:50]}..."
            )
            return True

        except Exception as e:
            logger.error(f"Episodic memory storage failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="episodic",
                reason=f"Failed to store episodic event: {str(e)}",
            ) from e

    async def retrieve_episodic_memories(
        self,
        user_id: str,
        query: str,
        event_types: list[EpisodicEventType] | None = None,
        top_k: int = 5,
    ) -> dict[str, Any]:
        """
        Retrieve relevant episodic memories via semantic search.

        Args:
            user_id: User identifier
            query: Query text to search for
            event_types: Optional list of event types to filter by
            top_k: Number of memories to retrieve

        Returns:
            Dict with context string and metadata

        Examples:
            from ..utils.user_config import get_user_id

            # Get all user preferences
            await retrieve_episodic_memories(
                user_id=get_user_id(),
                query="workout preferences",
                event_types=[EpisodicEventType.PREFERENCE]
            )

            # Get user goals and health events
            await retrieve_episodic_memories(
                user_id=get_user_id(),
                query="fitness goals",
                event_types=[EpisodicEventType.GOAL, EpisodicEventType.HEALTH_EVENT]
            )
        """
        if not self.episodic_index:
            return {"context": None, "hits": 0, "memories": []}

        try:
            # Generate query embedding using centralized service
            query_embedding = await self.embedding_service.generate_embedding(query)
            if query_embedding is None:
                return {"context": None, "hits": 0, "memories": []}

            # Build filter for user
            filter_expr = Tag("user_id") == user_id

            # Add event_type filtering if specified
            if event_types:
                event_type_values = [et.value for et in event_types]
                # Create OR condition for multiple event types
                if len(event_type_values) == 1:
                    filter_expr = filter_expr & (
                        Tag("event_type") == event_type_values[0]
                    )
                else:
                    # For multiple types, we need to use | (OR) operator
                    type_filters = [Tag("event_type") == et for et in event_type_values]
                    combined_type_filter = type_filters[0]
                    for tf in type_filters[1:]:
                        combined_type_filter = combined_type_filter | tf
                    filter_expr = filter_expr & combined_type_filter

            # Create vector query
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=[
                    "description",
                    "context",
                    "event_type",
                    "timestamp",
                    "metadata",
                ],
                filter_expression=filter_expr,
                num_results=top_k,
            )

            # Execute search
            results = self.episodic_index.query(vector_query)

            if not results:
                return {"context": None, "hits": 0, "memories": []}

            # Format results
            memories = []
            context_lines = ["Episodic memories (user-specific):"]

            for i, result in enumerate(results, 1):
                timestamp = result.get("timestamp")
                event_type = result.get("event_type", "unknown")
                description = result.get("description", "")
                context_text = result.get("context", "")

                # Format timestamp
                try:
                    dt = datetime.fromtimestamp(float(timestamp))
                    time_str = dt.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    time_str = "unknown"

                context_lines.append(f"\n{i}. [{time_str}] {event_type.upper()}")
                context_lines.append(f"   {description}")
                if context_text:
                    context_lines.append(f"   Context: {context_text[:100]}...")

                memories.append(
                    {
                        "event_type": event_type,
                        "description": description,
                        "context": context_text,
                        "timestamp": timestamp,
                        "metadata": json.loads(result.get("metadata", "{}")),
                    }
                )

            context = "\n".join(context_lines)

            return {"context": context, "hits": len(memories), "memories": memories}

        except Exception as e:
            logger.error(f"Episodic memory retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="episodic",
                reason=f"Failed to retrieve episodic memories: {str(e)}",
            ) from e

    async def get_user_preferences(
        self, user_id: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get user preferences specifically.

        Args:
            user_id: User identifier
            top_k: Number of preferences to retrieve

        Returns:
            List of preference memories
        """
        result = await self.retrieve_episodic_memories(
            user_id=user_id,
            query="user preferences",
            event_types=[EpisodicEventType.PREFERENCE],
            top_k=top_k,
        )
        return result.get("memories", [])

    async def get_user_goals(
        self, user_id: str, top_k: int = 5
    ) -> list[dict[str, Any]]:
        """
        Get user goals specifically.

        Args:
            user_id: User identifier
            top_k: Number of goals to retrieve

        Returns:
            List of goal memories
        """
        result = await self.retrieve_episodic_memories(
            user_id=user_id,
            query="user goals",
            event_types=[EpisodicEventType.GOAL],
            top_k=top_k,
        )
        return result.get("memories", [])

    async def clear_episodic_memories(self, user_id: str) -> dict[str, int]:
        """
        Clear all episodic memories for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict with count of deleted keys
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Clear all episodic memories for this user
                pattern = f"episodic:{user_id}:*"
                cursor = 0
                deleted_count = 0

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    if keys:
                        redis_client.delete(*keys)
                        deleted_count += len(keys)

                    if cursor == 0:
                        break

            logger.info(
                f"Cleared {deleted_count} episodic memories for user: {user_id}"
            )
            return {"deleted_count": deleted_count, "user_id": user_id}

        except Exception as e:
            logger.error(f"Episodic memory clearing failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="episodic",
                reason=f"Failed to clear episodic memories: {str(e)}",
            ) from e


# Global episodic memory manager instance
_episodic_memory_manager: EpisodicMemoryManager | None = None


def get_episodic_memory_manager() -> EpisodicMemoryManager:
    """
    Get or create the global episodic memory manager.

    Returns:
        EpisodicMemoryManager instance
    """
    global _episodic_memory_manager

    if _episodic_memory_manager is None:
        _episodic_memory_manager = EpisodicMemoryManager()

    return _episodic_memory_manager
