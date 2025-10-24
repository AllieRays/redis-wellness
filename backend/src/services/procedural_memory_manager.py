"""
Procedural Memory Manager - Learn and orchestrate successful tool-calling patterns.

Built from scratch with vector search and orchestration capabilities.
Uses RedisVL for semantic pattern matching (like episodic memory).

Architecture:
- Pattern storage: Query type, tools used, success score, timing
- Pattern retrieval: Semantic vector search for similar workflows
- Helper functions: Query classification, planning, evaluation (all embedded)
- Single-user focused: No per-user filtering needed
"""

import hashlib
import json
import logging
from datetime import UTC, datetime

import numpy as np
from redisvl.index import SearchIndex
from redisvl.query import VectorQuery
from redisvl.schema import IndexSchema

from ..config import get_settings
from .embedding_service import get_embedding_service
from .redis_connection import get_redis_manager

logger = logging.getLogger(__name__)


# ==================== EMBEDDED HELPER FUNCTIONS ====================
# These functions are embedded here to keep procedural memory isolated
# from the stateless agent (which cannot access services/)


def _classify_query(query: str) -> str:
    """
    Classify query into a type for pattern matching.

    Simple keyword-based classification. Keeps it simple and predictable.

    Query Types:
    - weight_analysis: "weight trend", "losing weight", "weight pattern"
    - workout_analysis: "workout schedule", "exercise pattern", "training"
    - comparison: "compare", "vs", "difference between"
    - progress: "progress", "improvement", "getting better"
    - health_metric: General health queries (heart rate, steps, etc.)

    Args:
        query: User query string

    Returns:
        Query type string
    """
    query_lower = query.lower()

    # Weight-related
    if any(
        kw in query_lower
        for kw in [
            "weight trend",
            "weight pattern",
            "losing weight",
            "gaining weight",
            "weight change",
        ]
    ):
        return "weight_analysis"

    # Workout-related
    if any(
        kw in query_lower
        for kw in [
            "workout",
            "exercise",
            "training",
            "activity pattern",
            "workout schedule",
        ]
    ):
        return "workout_analysis"

    # Comparison queries
    if any(
        kw in query_lower for kw in ["compare", " vs ", "versus", "difference between"]
    ):
        return "comparison"

    # Progress tracking
    if any(
        kw in query_lower
        for kw in ["progress", "improvement", "getting better", "improving"]
    ):
        return "progress"

    # Default to general health metric query
    return "health_metric"


def _plan_tool_sequence(query: str, query_type: str, past_patterns: list[dict]) -> dict:
    """
    Plan tool execution sequence based on query and past successful patterns.

    Simple planning strategy:
    1. If we have past patterns for this query type, suggest those tools
    2. Otherwise, suggest default tools based on query type
    3. LLM can review and modify the plan

    Args:
        query: User query string
        query_type: Classified query type
        past_patterns: List of similar successful patterns from memory

    Returns:
        Execution plan dict with suggested tools and reasoning
    """
    plan = {
        "query": query,
        "query_type": query_type,
        "suggested_tools": [],
        "reasoning": "",
        "confidence": 0.0,
    }

    # If we have past patterns, use the most successful one
    if past_patterns:
        best_pattern = max(past_patterns, key=lambda p: p.get("success_score", 0.0))
        plan["suggested_tools"] = best_pattern.get("tools_used", [])
        plan["reasoning"] = (
            f"Based on previous successful workflow (success: {best_pattern['success_score']:.0%})"
        )
        plan["confidence"] = best_pattern.get("success_score", 0.5)
        logger.info(
            f"📋 Planned from pattern: {len(plan['suggested_tools'])} tools, confidence={plan['confidence']:.2%}"
        )
        return plan

    # Otherwise, suggest default tools for query type
    default_tools = {
        "weight_analysis": [
            "search_health_records_by_metric",
            "aggregate_metrics",
            "calculate_weight_trends_tool",
        ],
        "workout_analysis": [
            "search_workouts_and_activity",
            "get_workout_schedule_analysis",
        ],
        "comparison": ["search_health_records_by_metric", "compare_time_periods_tool"],
        "progress": ["search_health_records_by_metric", "get_workout_progress"],
        "health_metric": ["search_health_records_by_metric"],  # Simple default
    }

    plan["suggested_tools"] = default_tools.get(
        query_type, ["search_health_records_by_metric"]
    )
    plan["reasoning"] = f"Default tool sequence for {query_type} queries"
    plan["confidence"] = 0.3  # Low confidence for defaults

    logger.info(
        f"📋 Planned from defaults: {len(plan['suggested_tools'])} tools, confidence={plan['confidence']:.2%}"
    )
    return plan


def _evaluate_workflow_success(
    tools_used: list[str],
    tool_results: list[dict],
    response_generated: bool,
    execution_time_ms: int,
) -> dict:
    """
    Evaluate if workflow was successful and should be stored.

    Success criteria:
    - All tools executed without errors
    - Response was generated
    - Reasonable execution time (< 30 seconds)

    Args:
        tools_used: List of tools that were called
        tool_results: Results from each tool call
        response_generated: Whether LLM generated a response
        execution_time_ms: Total execution time

    Returns:
        Evaluation dict with success_score and reasons
    """
    evaluation = {
        "success": False,
        "success_score": 0.0,
        "reasons": [],
    }

    # Check if any tools were called
    if not tools_used:
        evaluation["reasons"].append("No tools were called")
        logger.warning("⚠️ Workflow evaluation: No tools called")
        return evaluation

    # Check for tool errors
    errors = [r for r in tool_results if "error" in str(r.get("content", "")).lower()]
    if errors:
        evaluation["reasons"].append(f"{len(errors)} tool errors detected")
        evaluation["success_score"] = 0.3
        logger.warning(f"⚠️ Workflow evaluation: {len(errors)} tool errors")
        return evaluation

    # Check if response was generated
    if not response_generated:
        evaluation["reasons"].append("No response generated")
        evaluation["success_score"] = 0.2
        logger.warning("⚠️ Workflow evaluation: No response generated")
        return evaluation

    # Check execution time
    if execution_time_ms > 30000:  # 30 seconds
        evaluation["reasons"].append(f"Slow execution: {execution_time_ms / 1000:.1f}s")
        evaluation["success_score"] = 0.6
        logger.warning(f"⚠️ Workflow evaluation: Slow execution ({execution_time_ms}ms)")
    else:
        evaluation["success_score"] = 0.95  # Successful workflow
        evaluation["success"] = True
        evaluation["reasons"].append(
            "All criteria met: tools executed, response generated, good timing"
        )
        logger.info(
            f"✅ Workflow evaluation: Success (score={evaluation['success_score']:.2%})"
        )

    return evaluation


# ==================== MAIN PROCEDURAL MEMORY MANAGER ====================


class ProceduralMemoryManager:
    """
    Procedural Memory - Stores and retrieves successful tool-calling patterns.

    Uses vector search to find similar queries and suggests proven workflows.
    Includes planning, execution, and reflection capabilities.
    """

    PROCEDURAL_INDEX_NAME = "procedural_memory_idx"
    PROCEDURAL_PREFIX = "procedural:"

    def __init__(self) -> None:
        self.settings = get_settings()
        self.redis_manager = get_redis_manager()
        self.embedding_service = get_embedding_service()
        self.procedural_index = None

        # Initialize RedisVL index
        self._initialize_index()

        logger.info("✅ ProceduralMemoryManager initialized")

    def _initialize_index(self) -> None:
        """Create RedisVL index for procedural memory."""
        try:
            schema = IndexSchema.from_dict(
                {
                    "index": {
                        "name": self.PROCEDURAL_INDEX_NAME,
                        "prefix": self.PROCEDURAL_PREFIX,
                        "storage_type": "hash",
                    },
                    "fields": [
                        {
                            "name": "query_type",
                            "type": "tag",
                        },  # weight_analysis, workout_analysis, etc.
                        {"name": "timestamp", "type": "numeric"},
                        {
                            "name": "query_description",
                            "type": "text",
                        },  # "Analyze weight trends over time"
                        {"name": "tools_used", "type": "text"},  # JSON list of tools
                        {"name": "success_score", "type": "numeric"},
                        {"name": "execution_time_ms", "type": "numeric"},
                        {
                            "name": "metadata",
                            "type": "text",
                        },  # JSON: additional context
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

            self.procedural_index = SearchIndex(schema=schema)

            # Connect to Redis
            redis_url = f"redis://{self.settings.redis_host}:{self.settings.redis_port}/{self.settings.redis_db}"
            self.procedural_index.connect(redis_url)

            # Create index (don't overwrite if exists)
            try:
                self.procedural_index.create(overwrite=False)
                logger.info("📊 Created procedural memory index")
            except Exception:
                logger.info("📊 Procedural memory index already exists")

        except Exception as e:
            logger.error(f"❌ Failed to initialize procedural index: {e}")
            self.procedural_index = None

    async def store_pattern(
        self,
        query: str,
        tools_used: list[str],
        success_score: float,
        execution_time_ms: int,
        metadata: dict | None = None,
    ) -> bool:
        """
        Store a successful workflow pattern.

        Args:
            query: Original user query
            tools_used: List of tools that were called
            success_score: Success score (0.0-1.0)
            execution_time_ms: Execution time in milliseconds
            metadata: Optional additional context

        Returns:
            True if stored successfully
        """
        if not self.procedural_index:
            logger.error("❌ Procedural index not initialized")
            return False

        if success_score < 0.7:
            logger.info(f"⏭️ Skipping pattern storage (low score: {success_score:.2%})")
            return False

        try:
            # Classify query
            query_type = _classify_query(query)

            # Generate embedding for semantic search
            query_description = f"{query_type}: {query}"
            embedding = await self.embedding_service.generate_embedding(
                query_description
            )

            if not embedding:
                logger.error("❌ Failed to generate embedding for pattern")
                return False

            # Generate pattern ID (hash of query + tools)
            pattern_content = f"{query}:{':'.join(sorted(tools_used))}"
            pattern_hash = hashlib.sha256(pattern_content.encode()).hexdigest()[:12]

            # Create Redis key (single user, but use wellness_user for consistency)
            timestamp = int(datetime.now(UTC).timestamp())
            pattern_key = f"{self.PROCEDURAL_PREFIX}{pattern_hash}:{timestamp}"

            # Store pattern data
            pattern_data = {
                "query_type": query_type,
                "timestamp": timestamp,
                "query_description": query_description,
                "tools_used": json.dumps(tools_used),
                "success_score": success_score,
                "execution_time_ms": execution_time_ms,
                "metadata": json.dumps(metadata or {}),
                "embedding": np.array(embedding, dtype=np.float32).tobytes(),
            }

            # Use context manager to get connection
            with self.redis_manager.get_connection() as redis_client:
                redis_client.hset(pattern_key, mapping=pattern_data)

                # Set TTL (7 months)
                ttl_seconds = self.settings.redis_session_ttl_seconds  # 7 months
                redis_client.expire(pattern_key, ttl_seconds)

            logger.info(
                f"💾 Stored procedural pattern: {query_type}, {len(tools_used)} tools, score={success_score:.2%}"
            )
            return True

        except Exception as e:
            logger.error(f"❌ Failed to store procedural pattern: {e}")
            return False

    async def retrieve_patterns(self, query: str, top_k: int = 3) -> dict:
        """
        Retrieve similar successful patterns via semantic search.

        Args:
            query: Current user query
            top_k: Number of similar patterns to retrieve

        Returns:
            Dict with patterns, query_type, and execution plan
        """
        if not self.procedural_index:
            logger.warning("⚠️ Procedural index not initialized")
            return {"patterns": [], "query_type": "unknown", "plan": None}

        try:
            # Classify query
            query_type = _classify_query(query)

            # Generate embedding for search
            query_description = f"{query_type}: {query}"
            query_embedding = await self.embedding_service.generate_embedding(
                query_description
            )

            if not query_embedding:
                logger.error("❌ Failed to generate query embedding")
                return {"patterns": [], "query_type": query_type, "plan": None}

            # Build vector query (no user filter - global patterns)
            vector_query = VectorQuery(
                vector=query_embedding,
                vector_field_name="embedding",
                num_results=top_k,
                return_fields=[
                    "query_type",
                    "query_description",
                    "tools_used",
                    "success_score",
                    "execution_time_ms",
                ],
            )

            # Execute search
            results = self.procedural_index.query(vector_query)

            # Parse results
            patterns = []
            for result in results:
                try:
                    patterns.append(
                        {
                            "query_type": result.get("query_type", "unknown"),
                            "query_description": result.get("query_description", ""),
                            "tools_used": json.loads(result.get("tools_used", "[]")),
                            "success_score": float(result.get("success_score", 0.0)),
                            "execution_time_ms": int(
                                result.get("execution_time_ms", 0)
                            ),
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Failed to parse pattern result: {e}")
                    continue

            logger.info(
                f"🧠 Retrieved {len(patterns)} procedural patterns for query_type={query_type}"
            )

            # Create execution plan
            plan = _plan_tool_sequence(query, query_type, patterns)

            return {
                "patterns": patterns,
                "query_type": query_type,
                "plan": plan,
            }

        except Exception as e:
            logger.error(f"❌ Failed to retrieve procedural patterns: {e}")
            return {"patterns": [], "query_type": "unknown", "plan": None}

    def evaluate_workflow(
        self,
        tools_used: list[str],
        tool_results: list[dict],
        response_generated: bool,
        execution_time_ms: int,
    ) -> dict:
        """
        Evaluate workflow success (wrapper for embedded function).

        Args:
            tools_used: List of tools that were called
            tool_results: Results from each tool call
            response_generated: Whether LLM generated a response
            execution_time_ms: Total execution time

        Returns:
            Evaluation dict with success_score
        """
        return _evaluate_workflow_success(
            tools_used, tool_results, response_generated, execution_time_ms
        )


# ==================== SINGLETON ====================

_procedural_memory = None


def get_procedural_memory() -> ProceduralMemoryManager | None:
    """Get or create singleton procedural memory manager instance."""
    global _procedural_memory
    if _procedural_memory is None:
        try:
            _procedural_memory = ProceduralMemoryManager()
        except Exception as e:
            logger.error(f"❌ Failed to initialize procedural memory: {e}")
            return None
    return _procedural_memory
