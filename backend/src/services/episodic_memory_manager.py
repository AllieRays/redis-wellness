"""
Minimal Episodic Memory Manager - Store and retrieve user goals.

Focused implementation for goal storage/retrieval only.
Uses RedisVL for vector search.
"""

import json
import logging
from typing import Any

import numpy as np
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from redisvl.schema import IndexSchema

from ..config import get_settings
from ..utils.exceptions import MemoryRetrievalError, MemoryStorageError
from ..utils.redis_keys import RedisKeys
from ..utils.time_utils import get_utc_timestamp
from .embedding_service import get_embedding_service
from .redis_connection import get_redis_manager, get_redis_url

logger = logging.getLogger(__name__)


class EpisodicMemoryManager:
    """
    Minimal episodic memory - stores ONLY goals for now.

    Example: "User's weight goal is 125 lbs"
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis_manager = get_redis_manager()
        self.embedding_service = get_embedding_service()
        self.episodic_index = None

        # Initialize RedisVL index
        self._initialize_index()

        logger.info("✅ EpisodicMemoryManager initialized")

    def _initialize_index(self) -> None:
        """Create RedisVL index for episodic memory."""
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
                        {
                            "name": "event_type",
                            "type": "tag",
                        },  # "goal", "preference", etc.
                        {"name": "timestamp", "type": "numeric"},
                        {
                            "name": "description",
                            "type": "text",
                        },  # "User's weight goal is 125 lbs"
                        {
                            "name": "metadata",
                            "type": "text",
                        },  # JSON: {"metric": "weight", "value": 125, "unit": "lbs"}
                        {
                            "name": "embedding",
                            "type": "vector",
                            "attrs": {
                                "dims": 1024,
                                "distance_metric": "cosine",
                                "algorithm": "hnsw",
                                "datatype": "float32",
                            },
                        },
                    ],
                }
            )

            self.episodic_index = SearchIndex(schema=schema)

            # Connect to Redis using centralized utility
            redis_url = get_redis_url(
                host=self.settings.redis_host,
                port=self.settings.redis_port,
                db=self.settings.redis_db,
            )
            self.episodic_index.connect(redis_url)

            # Create index (don't overwrite if exists)
            try:
                self.episodic_index.create(overwrite=False)
                logger.info("📊 Created episodic memory index")
            except Exception:
                logger.info("📊 Episodic memory index already exists")

        except Exception as e:
            logger.error(f"❌ Failed to initialize episodic index: {e}")
            self.episodic_index = None

    async def store_goal(
        self,
        user_id: str,
        metric: str,
        value: float | int,
        unit: str,
    ) -> bool:
        """
        Store a user goal in episodic memory.

        Args:
            user_id: User identifier
            metric: Goal metric (e.g., "weight", "bmi")
            value: Goal value (e.g., 125)
            unit: Unit (e.g., "lbs", "kg")

        Returns:
            True if stored successfully

        Example:
            await store_goal(user_id="wellness_user", metric="weight", value=125, unit="lbs")
            # Stores: "User's weight goal is 125 lbs" with embedding
        """
        if not self.episodic_index:
            logger.error("Episodic index not initialized")
            return False

        try:
            # Create description for embedding
            description = f"User's {metric} goal is {value} {unit}"

            # Generate embedding
            embedding = await self.embedding_service.generate_embedding(description)
            if embedding is None:
                logger.error("Failed to generate embedding for goal")
                return False

            # Create memory record using centralized utilities
            timestamp = get_utc_timestamp()
            memory_key = RedisKeys.episodic_memory(user_id, "goal", timestamp)

            metadata = {
                "metric": metric,
                "value": value,
                "unit": unit,
            }

            memory_data = {
                "user_id": user_id,
                "event_type": "goal",
                "timestamp": timestamp,
                "description": description,
                "metadata": json.dumps(metadata),
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }

            # Store in Redis
            with self.redis_manager.get_connection() as redis_client:
                redis_client.hset(memory_key, mapping=memory_data)
                # Set TTL (7 months)
                redis_client.expire(memory_key, self.settings.redis_session_ttl_seconds)

            logger.info(f"💾 Stored goal: {description}")
            return True

        except Exception as e:
            logger.error(f"❌ Goal storage failed: {e}", exc_info=True)
            raise MemoryStorageError(
                memory_type="episodic",
                reason=f"Failed to store goal: {str(e)}",
            ) from e

    async def retrieve_goals(
        self,
        user_id: str,
        query: str,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """
        Retrieve user goals via semantic search.

        Args:
            user_id: User identifier
            query: Query text (e.g., "what's my goal", "weight target")
            top_k: Number of results to return

        Returns:
            Dict with:
            - context: Formatted string for LLM prompt
            - hits: Number of memories found
            - goals: List of goal metadata

        Example:
            result = await retrieve_goals(user_id="wellness_user", query="what's my weight goal")
            # Returns: {"context": "Weight goal: 125 lbs", "hits": 1, "goals": [{"metric": "weight", ...}]}
        """
        if not self.episodic_index:
            return {"context": None, "hits": 0, "goals": []}

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            if query_embedding is None:
                return {"context": None, "hits": 0, "goals": []}

            # Build filter: user_id AND event_type=goal
            filter_expr = Tag("user_id") == user_id
            filter_expr = filter_expr & (Tag("event_type") == "goal")

            # Create vector query
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=["description", "metadata", "timestamp"],
                filter_expression=filter_expr,
                num_results=top_k,
            )

            # Execute search
            results = self.episodic_index.query(vector_query)

            if not results:
                return {"context": None, "hits": 0, "goals": []}

            # Format results for LLM
            goals = []
            context_lines = []

            for result in results:
                metadata = json.loads(result.get("metadata", "{}"))
                # description = result.get("description", "")  # Not needed, using metadata

                goals.append(metadata)
                # Format: "Weight goal: 125 lbs"
                context_lines.append(
                    f"{metadata['metric'].capitalize()} goal: {metadata['value']} {metadata['unit']}"
                )

            context = "\n".join(context_lines)

            logger.info(f"🔍 Retrieved {len(results)} goals for query: {query[:50]}")
            return {
                "context": context,
                "hits": len(results),
                "goals": goals,
            }

        except Exception as e:
            logger.error(f"❌ Goal retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="episodic",
                reason=f"Failed to retrieve goals: {str(e)}",
            ) from e


# Singleton instance
_episodic_memory: EpisodicMemoryManager | None = None


def get_episodic_memory() -> EpisodicMemoryManager:
    """Get or create singleton episodic memory manager."""
    global _episodic_memory
    if _episodic_memory is None:
        _episodic_memory = EpisodicMemoryManager()
    return _episodic_memory
