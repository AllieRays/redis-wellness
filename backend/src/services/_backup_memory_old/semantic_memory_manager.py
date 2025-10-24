"""
Semantic Memory Manager - Stores general health knowledge and facts.

Based on CoALA framework (https://arxiv.org/pdf/2309.02427):
"Semantic memory stores general knowledge, facts, concepts, and relationships,
composing the AI's knowledge base about the world."

Examples of Semantic Memories:
- General health facts: "Normal resting heart rate is 60-100 bpm"
- Medical knowledge: "VO2 max is a measure of cardiovascular fitness"
- Health concepts: "BMI is calculated as weight(kg) / height(m)²"
- Relationships: "Higher VO2 max correlates with better endurance"

Storage Strategy:
- RedisVL vector index for semantic search
- Prefix: semantic:{fact_id}
- Stores general knowledge, NOT user-specific data
- Separate from episodic (user events) and procedural (tool sequences)
"""

import json
import logging
from datetime import UTC, datetime
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


class SemanticMemoryManager:
    """
    Manages semantic memories: general health knowledge and facts.

    Semantic memory is impersonal and factual - it stores:
    - General health knowledge (not user-specific)
    - Medical facts and concepts
    - Health metric definitions
    - Relationships between health concepts

    This is separate from episodic memory (user-specific events)
    and procedural memory (learned tool sequences).
    """

    def __init__(self) -> None:
        """Initialize semantic memory manager with RedisVL index."""
        self.settings = get_settings()
        self.redis_manager = RedisConnectionManager()

        # Use centralized embedding service
        self.embedding_service = get_embedding_service()

        # Initialize RedisVL index for semantic memory
        self.semantic_index = None
        self._initialize_semantic_index()

        # TTL for semantic memories (7 months, same as other memories)
        self.memory_ttl = self.settings.redis_session_ttl_seconds

        logger.info("SemanticMemoryManager initialized successfully")

    def _initialize_semantic_index(self) -> None:
        """Initialize RedisVL index for semantic memory (general knowledge)."""
        try:
            schema = IndexSchema.from_dict(
                {
                    "index": {
                        "name": RedisKeys.SEMANTIC_KNOWLEDGE_INDEX,
                        "prefix": RedisKeys.SEMANTIC_PREFIX,
                        "storage_type": "hash",
                    },
                    "fields": [
                        {
                            "name": "fact_type",
                            "type": "tag",
                        },  # "definition", "relationship", "guideline"
                        {
                            "name": "category",
                            "type": "tag",
                        },  # "cardio", "nutrition", "metrics"
                        {"name": "timestamp", "type": "numeric"},
                        {"name": "fact", "type": "text"},
                        {"name": "context", "type": "text"},
                        {
                            "name": "source",
                            "type": "text",
                        },  # Where this knowledge came from
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

            self.semantic_index = SearchIndex(schema=schema)

            # Connect to Redis
            redis_url = f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"
            self.semantic_index.connect(redis_url)

            # Create index if it doesn't exist
            try:
                self.semantic_index.create(overwrite=False)
                logger.info("Created semantic knowledge index")
            except Exception:
                logger.info("Semantic knowledge index already exists")

        except Exception as e:
            logger.error(f"Failed to initialize semantic index: {e}")
            self.semantic_index = None

    async def store_semantic_fact(
        self,
        fact: str,
        fact_type: str = "general",  # "definition", "relationship", "guideline", "general"
        category: str = "general",  # "cardio", "nutrition", "metrics", "general"
        context: str = "",
        source: str = "system",
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a semantic fact (general health knowledge).

        Args:
            fact: The factual statement
            fact_type: Type of fact (definition, relationship, guideline)
            category: Health category (cardio, nutrition, metrics, etc.)
            context: Additional context about the fact
            source: Where this knowledge came from
            metadata: Additional structured data

        Returns:
            True if successful, False otherwise

        Examples:
            await store_semantic_fact(
                fact="Normal resting heart rate is 60-100 bpm",
                fact_type="guideline",
                category="cardio",
                context="Standard medical guideline for adults",
                source="medical_literature"
            )

            await store_semantic_fact(
                fact="VO2 max is a measure of cardiovascular fitness",
                fact_type="definition",
                category="metrics",
                context="Measures maximum oxygen consumption during exercise"
            )
        """
        if not self.semantic_index:
            return False

        try:
            # Combine fact and context for embedding
            combined_text = f"{fact}\n{context}" if context else fact

            # Generate embedding using centralized service
            embedding = await self.embedding_service.generate_embedding(combined_text)
            if embedding is None:
                return False

            # Create memory record
            timestamp = int(datetime.now(UTC).timestamp())
            memory_key = RedisKeys.semantic_memory(category, fact_type, timestamp)

            # Store in RedisVL
            with self.redis_manager.get_connection() as redis_client:
                import numpy as np

                memory_data = {
                    "fact_type": fact_type,
                    "category": category,
                    "timestamp": timestamp,
                    "fact": fact,
                    "context": context,
                    "source": source,
                    "metadata": json.dumps(metadata or {}),
                    "embedding": np.array(embedding, dtype=np.float32).tobytes(),
                }

                # Store as hash
                redis_client.hset(memory_key, mapping=memory_data)

                # Set TTL
                redis_client.expire(memory_key, self.memory_ttl)

            logger.info(f"Stored semantic fact: {fact[:50]}...")
            return True

        except Exception as e:
            logger.error(f"Semantic fact storage failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="semantic",
                reason=f"Failed to store semantic fact: {str(e)}",
            ) from e

    async def retrieve_semantic_knowledge(
        self,
        query: str,
        categories: list[str] | None = None,
        top_k: int = 3,
    ) -> dict[str, Any]:
        """
        Retrieve relevant semantic knowledge via vector search.

        Args:
            query: Query text to search for
            categories: Optional list of categories to filter by
            top_k: Number of facts to retrieve

        Returns:
            Dict with context string and metadata

        Examples:
            # Get general heart rate knowledge
            await retrieve_semantic_knowledge(
                query="heart rate zones",
                categories=["cardio"]
            )

            # Get BMI calculation info
            await retrieve_semantic_knowledge(
                query="BMI calculation",
                categories=["metrics", "nutrition"]
            )
        """
        if not self.semantic_index:
            return {"context": None, "hits": 0, "facts": []}

        try:
            # Generate query embedding using centralized service
            query_embedding = await self.embedding_service.generate_embedding(query)
            if query_embedding is None:
                return {"context": None, "hits": 0, "facts": []}

            # Build filter if categories specified
            filter_expr = None
            if categories:
                if len(categories) == 1:
                    filter_expr = Tag("category") == categories[0]
                else:
                    # Create OR condition for multiple categories
                    category_filters = [Tag("category") == cat for cat in categories]
                    filter_expr = category_filters[0]
                    for cf in category_filters[1:]:
                        filter_expr = filter_expr | cf

            # Create vector query
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                return_fields=["fact", "context", "fact_type", "category", "timestamp"],
                filter_expression=filter_expr,
                num_results=top_k,
            )

            # Execute search
            results = self.semantic_index.query(vector_query)

            if not results:
                return {"context": None, "hits": 0, "facts": []}

            # Format results
            facts = []
            context_lines = ["Semantic knowledge (general health facts):"]

            for i, result in enumerate(results, 1):
                fact = result.get("fact", "")
                context_text = result.get("context", "")
                fact_type = result.get("fact_type", "general")
                category = result.get("category", "general")

                context_lines.append(f"\n{i}. [{category.upper()}] {fact_type}")
                context_lines.append(f"   {fact}")
                if context_text:
                    context_lines.append(f"   {context_text[:100]}...")

                facts.append(
                    {
                        "fact": fact,
                        "context": context_text,
                        "fact_type": fact_type,
                        "category": category,
                    }
                )

            context = "\n".join(context_lines)

            return {"context": context, "hits": len(facts), "facts": facts}

        except Exception as e:
            logger.error(f"Semantic knowledge retrieval failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="semantic",
                reason=f"Failed to retrieve semantic knowledge: {str(e)}",
            ) from e

    async def populate_default_health_knowledge(self) -> int:
        """
        Populate semantic memory with default health knowledge.

        Returns:
            Number of facts stored
        """
        default_facts = [
            {
                "fact": "Normal resting heart rate for adults is 60-100 beats per minute",
                "fact_type": "guideline",
                "category": "cardio",
                "context": "Lower heart rate at rest generally indicates more efficient heart function and better cardiovascular fitness",
            },
            {
                "fact": "VO2 max is the maximum amount of oxygen the body can utilize during intense exercise",
                "fact_type": "definition",
                "category": "metrics",
                "context": "Measured in milliliters of oxygen per kilogram of body weight per minute (mL/kg/min)",
            },
            {
                "fact": "BMI is calculated as weight in kilograms divided by height in meters squared",
                "fact_type": "definition",
                "category": "metrics",
                "context": "BMI = weight(kg) / [height(m)]²",
            },
            {
                "fact": "Moderate intensity cardio exercise is 50-70% of maximum heart rate",
                "fact_type": "guideline",
                "category": "cardio",
                "context": "Maximum heart rate is roughly 220 minus your age",
            },
            {
                "fact": "Active energy is calories burned through physical activity",
                "fact_type": "definition",
                "category": "metrics",
                "context": "Excludes basal metabolic rate (BMR) - calories burned at rest",
            },
        ]

        stored_count = 0
        for fact_data in default_facts:
            success = await self.store_semantic_fact(**fact_data)
            if success:
                stored_count += 1

        logger.info(f"Populated {stored_count} default health facts")
        return stored_count

    async def clear_semantic_knowledge(
        self, category: str | None = None
    ) -> dict[str, int]:
        """
        Clear semantic knowledge (optionally filtered by category).

        Args:
            category: Optional category to clear (None = clear all)

        Returns:
            Dict with count of deleted keys
        """
        try:
            with self.redis_manager.get_connection() as redis_client:
                # Clear semantic memories
                if category:
                    pattern = f"{RedisKeys.SEMANTIC_PREFIX}{category}:*"
                else:
                    pattern = f"{RedisKeys.SEMANTIC_PREFIX}*"

                cursor = 0
                deleted_count = 0

                while True:
                    cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                    if keys:
                        redis_client.delete(*keys)
                        deleted_count += len(keys)

                    if cursor == 0:
                        break

            logger.info(f"Cleared {deleted_count} semantic facts")
            return {"deleted_count": deleted_count, "category": category or "all"}

        except Exception as e:
            logger.error(f"Semantic knowledge clearing failed: {e}", exc_info=True)
            raise MemoryRetrievalError(
                memory_type="semantic",
                reason=f"Failed to clear semantic knowledge: {str(e)}",
            ) from e


# Global semantic memory manager instance
_semantic_memory_manager: SemanticMemoryManager | None = None


def get_semantic_memory_manager() -> SemanticMemoryManager:
    """
    Get or create the global semantic memory manager.

    Returns:
        SemanticMemoryManager instance
    """
    global _semantic_memory_manager

    if _semantic_memory_manager is None:
        _semantic_memory_manager = SemanticMemoryManager()

    return _semantic_memory_manager
