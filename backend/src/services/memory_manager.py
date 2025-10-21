"""
Dual Memory System for Health RAG Agent.

Implements:
1. Short-term Memory: Conversation context (last 10 messages)
2. Long-term Memory: Semantic memory via RedisVL vector search

Architecture:
- Short-term: Fast Redis LIST for recent conversation
- Long-term: RedisVL HNSW index for semantic retrieval
- Both use TTL for automatic cleanup (7 months)
"""

import json
import logging
from datetime import datetime
from typing import Any

import httpx
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.query.filter import Tag
from redisvl.schema import IndexSchema

from ..config import get_settings
from .redis_connection import RedisConnectionManager

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Dual memory system for health conversations.

    Short-term: Recent conversation (10 messages)
    Long-term: Semantic search across all past conversations
    """

    def __init__(self):
        """Initialize memory manager with embedding model and Redis."""
        self.settings = get_settings()
        self.redis_manager = RedisConnectionManager()

        # Initialize Ollama client for embeddings
        self.ollama_base_url = self.settings.ollama_base_url
        self.embedding_model = self.settings.embedding_model
        logger.info(f"Using Ollama embedding model: {self.embedding_model}")

        # Initialize RedisVL index for semantic memory
        self.semantic_index = None
        self._initialize_semantic_index()

        # TTL for memories (7 months in seconds)
        self.memory_ttl = self.settings.redis_session_ttl_seconds

        logger.info("MemoryManager initialized successfully")

    def _initialize_semantic_index(self):
        """Initialize RedisVL index for semantic memory storage."""
        try:
            schema = IndexSchema.from_dict(
                {
                    "index": {
                        "name": "semantic_memory_idx",
                        "prefix": "memory:semantic:",
                        "storage_type": "hash",
                    },
                    "fields": [
                        {"name": "user_id", "type": "tag"},
                        {"name": "session_id", "type": "tag"},
                        {"name": "timestamp", "type": "numeric"},
                        {"name": "user_message", "type": "text"},
                        {"name": "assistant_response", "type": "text"},
                        {"name": "combined_text", "type": "text"},
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

            self.semantic_index = SearchIndex(schema=schema)

            # Connect to Redis
            redis_url = f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"
            self.semantic_index.connect(redis_url)

            # Create index if it doesn't exist
            try:
                self.semantic_index.create(overwrite=False)
                logger.info("Created semantic memory index")
            except Exception:
                logger.info("Semantic memory index already exists")

        except Exception as e:
            logger.error(f"Failed to initialize semantic index: {e}")
            self.semantic_index = None

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
                session_key = f"health_chat_session:{session_id}"

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

    # ========== LONG-TERM MEMORY (SEMANTIC) ==========

    async def _generate_embedding(self, text: str) -> list[float] | None:
        """Generate embedding using Ollama."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_base_url}/api/embeddings",
                    json={"model": self.embedding_model, "prompt": text},
                )
                response.raise_for_status()
                return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def store_semantic_memory(
        self, user_id: str, session_id: str, user_message: str, assistant_response: str
    ) -> bool:
        """
        Store conversation in semantic memory.

        Creates vector embedding and stores in RedisVL for later retrieval.

        Args:
            user_id: User identifier
            session_id: Session identifier
            user_message: User's message
            assistant_response: Assistant's response

        Returns:
            True if successful, False otherwise
        """
        if not self.semantic_index:
            return False

        try:
            # Combine user message and response for semantic search
            combined_text = f"User: {user_message}\nAssistant: {assistant_response}"

            # Generate embedding using Ollama
            embedding = await self._generate_embedding(combined_text)
            if embedding is None:
                return False

            # Create memory record
            timestamp = int(datetime.now().timestamp())
            memory_key = f"memory:semantic:{user_id}:{session_id}:{timestamp}"

            # Store in RedisVL
            with self.redis_manager.get_connection() as redis_client:
                import numpy as np

                memory_data = {
                    "user_id": user_id,
                    "session_id": session_id,
                    "timestamp": timestamp,
                    "user_message": user_message,
                    "assistant_response": assistant_response,
                    "combined_text": combined_text,
                    "embedding": np.array(embedding, dtype=np.float32).tobytes(),
                }

                # Store as hash
                redis_client.hset(memory_key, mapping=memory_data)

                # Set TTL
                redis_client.expire(memory_key, self.memory_ttl)

            logger.debug(f"Stored semantic memory: {memory_key[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Semantic memory storage failed: {e}")
            return False

    async def retrieve_semantic_memory(
        self, user_id: str, query: str, top_k: int = 3
    ) -> dict[str, Any]:
        """
        Retrieve relevant memories via semantic search.

        Args:
            user_id: User identifier
            query: Query text to search for
            top_k: Number of memories to retrieve

        Returns:
            Dict with context string and metadata
        """
        if not self.semantic_index:
            return {"context": None, "hits": 0, "memories": []}

        try:
            # Generate query embedding using Ollama
            query_embedding = await self._generate_embedding(query)
            if query_embedding is None:
                return {"context": None, "hits": 0, "memories": []}

            # Build filter for user
            filter_expr = Tag("user_id") == user_id

            # Create vector query
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=[
                    "user_message",
                    "assistant_response",
                    "timestamp",
                    "session_id",
                ],
                filter_expression=filter_expr,
                num_results=top_k,
            )

            # Execute search
            results = self.semantic_index.query(vector_query)

            if not results:
                return {"context": None, "hits": 0, "memories": []}

            # Format results
            memories = []
            context_lines = ["Relevant past insights:"]

            for i, result in enumerate(results, 1):
                timestamp = result.get("timestamp")
                user_msg = result.get("user_message", "")
                assistant_resp = result.get("assistant_response", "")

                # Format timestamp
                try:
                    dt = datetime.fromtimestamp(float(timestamp))
                    time_str = dt.strftime("%Y-%m-%d")
                except (ValueError, AttributeError):
                    time_str = "unknown"

                context_lines.append(f"\n{i}. [{time_str}]")
                context_lines.append(f"   Q: {user_msg[:100]}...")
                context_lines.append(f"   A: {assistant_resp[:150]}...")

                memories.append(
                    {
                        "user_message": user_msg,
                        "assistant_response": assistant_resp,
                        "timestamp": timestamp,
                        "session_id": result.get("session_id"),
                    }
                )

            context = "\n".join(context_lines)

            return {"context": context, "hits": len(memories), "memories": memories}

        except Exception as e:
            logger.error(f"Semantic memory retrieval failed: {e}")
            return {"context": None, "hits": 0, "memories": []}

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
                session_key = f"health_chat_session:{session_id}"
                redis_client.delete(session_key)

                # Clear semantic memories (scan and delete)
                pattern = f"memory:semantic:*:{session_id}:*"
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
                session_key = f"health_chat_session:{session_id}"
                short_term_count = redis_client.llen(session_key)
                short_term_ttl = redis_client.ttl(session_key)

                # Long-term stats (approximate via scan)
                pattern = f"memory:semantic:{user_id}:*"
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
                        "semantic_search_enabled": self.semantic_index is not None,
                    },
                    "user_id": user_id,
                    "session_id": session_id,
                }

        except Exception as e:
            logger.error(f"Memory stats retrieval failed: {e}")
            return {"error": str(e)}


# Global memory manager instance
_memory_manager: MemoryManager | None = None


def get_memory_manager() -> MemoryManager:
    """
    Get or create the global memory manager.

    Returns:
        MemoryManager instance
    """
    global _memory_manager

    if _memory_manager is None:
        _memory_manager = MemoryManager()

    return _memory_manager
