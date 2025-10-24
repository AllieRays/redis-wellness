"""
System Routes - Main API Router and System Health Monitoring

This module serves as the central system router that:
1. Aggregates all API route modules
2. Provides system health monitoring endpoints
3. Monitors critical system dependencies (Redis, Ollama, AI tools)
"""

import logging
import os

import httpx
import redis
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from ..utils.exceptions import generate_correlation_id
from .chat_routes import router as chat_router
from .models.errors import internal_error, service_error

logger = logging.getLogger(__name__)

# ========== Router Setup ==========

router = APIRouter()

router.include_router(chat_router)


# ========== Health Check Models ==========


class HealthCheck(BaseModel):
    """Simple system health check response."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    redis_connected: bool
    redis_stack_available: bool
    ollama_connected: bool


# ========== System Dependency Checks ==========


def get_redis_client() -> redis.Redis:
    """Create Redis client for health checks."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=False,  # Keep as bytes for MODULE LIST parsing
    )


async def check_redis_connection() -> bool:
    """Check if Redis is reachable."""
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        return True
    except Exception:
        return False


async def check_redis_stack_modules() -> bool:
    """
    Check if Redis Stack modules are loaded (RediSearch, RedisJSON, etc.).

    This is CRITICAL for episodic and procedural memory to work.
    Without RediSearch module, vector search commands (FT.SEARCH) will fail.
    """
    try:
        redis_client = get_redis_client()
        modules = redis_client.execute_command("MODULE", "LIST")

        # Check for RediSearch module (required for vector search)
        # MODULE LIST returns: [b'name', b'search', b'ver', 21005, ...]
        # Check if any item in the list contains 'search' (case-insensitive)
        has_search = any(
            b"search"
            in (item if isinstance(item, bytes) else str(item).encode()).lower()
            for item in modules
        )

        if not has_search:
            logger.warning("⚠️  Redis is connected but RediSearch module is NOT loaded!")
            logger.warning("    Episodic and procedural memory will NOT work.")
            logger.warning("    Please use Redis Stack instead of base Redis.")

        return has_search
    except Exception as e:
        logger.error(f"Failed to check Redis modules: {e}")
        return False


async def check_ollama_connection() -> bool:
    """Check if Ollama is running."""
    try:
        from ..config import get_settings

        settings = get_settings()

        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.ollama_base_url}")
            return response.status_code == 200
    except Exception:
        return False


# ========== Health Check Endpoint ==========


@router.get("/health/check", response_model=HealthCheck)
async def health_check():
    """
    System health check for the wellness app.

    Checks:
    - Redis connectivity
    - Redis Stack modules (RediSearch for vector search)
    - Ollama connectivity

    Note: redis_stack_available must be True for episodic/procedural memory to work.
    """
    correlation_id = generate_correlation_id()

    try:
        redis_ok = await check_redis_connection()
        redis_stack_ok = await check_redis_stack_modules() if redis_ok else False
        ollama_ok = await check_ollama_connection()

        # System is only fully healthy if Redis Stack modules are available
        status = "healthy" if redis_ok and redis_stack_ok and ollama_ok else "unhealthy"

        return HealthCheck(
            status=status,
            redis_connected=redis_ok,
            redis_stack_available=redis_stack_ok,
            ollama_connected=ollama_ok,
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        error_response = internal_error(
            message="Health check failed",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=500, detail=error_response.dict()) from e


# ========== Embedding Cache Stats Endpoint ==========


@router.get("/cache/embedding/stats")
async def get_embedding_cache_stats():
    """
    Get embedding cache performance statistics.

    Shows:
    - Cache hits vs misses
    - Hit rate percentage
    - Estimated time saved (ms)
    - Cache TTL configuration

    Use this endpoint to monitor cache effectiveness.
    A high hit rate (>30%) indicates the cache is working well.

    Returns:
        Dict with cache performance metrics
    """
    correlation_id = generate_correlation_id()

    try:
        from ..services.embedding_cache import get_embedding_cache

        cache = get_embedding_cache()
        stats = cache.get_stats()

        return {
            "embedding_cache": stats,
            "description": "Embedding cache statistics (caches Ollama embedding generation)",
            "note": "High hit rate = faster semantic memory searches",
        }
    except Exception as e:
        logger.error(f"Failed to get embedding cache stats: {e}", exc_info=True)
        error_response = service_error(
            service="embedding_cache",
            reason=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=503, detail=error_response.dict()) from e


# ========== Semantic Memory Audit Endpoints ==========


@router.get("/memory/semantic/stats")
async def get_semantic_memory_stats():
    """
    Get semantic memory statistics.

    Shows:
    - Total number of facts stored
    - Breakdown by category (metrics, cardio, exercise, sleep, recovery)
    - Breakdown by fact type (definition, guideline, relationship)
    - Breakdown by confidence level (high, medium)
    - List of authoritative sources

    Use this to audit the semantic knowledge base and ensure
    only verified facts are loaded.

    Returns:
        Dict with semantic memory statistics
    """
    correlation_id = generate_correlation_id()

    try:
        from ..utils.redis_keys import RedisKeys

        # Use raw Redis client (decode_responses=False to handle binary embeddings)
        redis_client = get_redis_client()

        try:
            # Get all semantic memory keys
            pattern = f"{RedisKeys.SEMANTIC_PREFIX}*"
            cursor = 0
            all_keys = []

            while True:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
                all_keys.extend(keys)
                if cursor == 0:
                    break

            # Analyze facts
            stats = {
                "total_facts": len(all_keys),
                "categories": {},
                "fact_types": {},
                "confidence_levels": {"high": 0, "medium": 0, "unknown": 0},
                "sources": set(),
            }

            for key in all_keys:
                try:
                    fact_data = redis_client.hgetall(key)

                    # Helper to get string value (handle both bytes and str)
                    def get_str_value(data, field, default="unknown"):
                        value = data.get(field.encode(), data.get(field, default))
                        if isinstance(value, bytes):
                            return value.decode()
                        return value

                    # Get category
                    category = get_str_value(fact_data, "category")
                    if category not in stats["categories"]:
                        stats["categories"][category] = 0
                    stats["categories"][category] += 1

                    # Get fact type
                    fact_type = get_str_value(fact_data, "fact_type")
                    if fact_type not in stats["fact_types"]:
                        stats["fact_types"][fact_type] = 0
                    stats["fact_types"][fact_type] += 1

                    # Get confidence level from metadata
                    import json

                    metadata_str = get_str_value(fact_data, "metadata", "{}")
                    metadata = json.loads(metadata_str)
                    confidence = metadata.get("confidence", "unknown")
                    if confidence in stats["confidence_levels"]:
                        stats["confidence_levels"][confidence] += 1
                    else:
                        stats["confidence_levels"]["unknown"] += 1

                    # Get source
                    source = get_str_value(fact_data, "source")
                    if source != "unknown":
                        stats["sources"].add(source)

                except Exception as e:
                    logger.warning(f"Failed to parse fact {key}: {e}")
                    continue

            # Convert sources set to list for JSON serialization
            stats["sources"] = sorted(stats["sources"])

            return {
                "semantic_memory": stats,
                "description": "Statistics about verified health facts in semantic memory",
                "note": "All facts should have authoritative sources and confidence levels",
            }

        finally:
            redis_client.close()

    except Exception as e:
        logger.error(f"Failed to get semantic memory stats: {e}", exc_info=True)
        error_response = service_error(
            service="semantic_memory",
            reason=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=503, detail=error_response.dict()) from e


@router.get("/memory/semantic/facts")
async def get_semantic_facts(
    category: str | None = None,
    fact_type: str | None = None,
    limit: int = 50,
):
    """
    Get semantic facts for audit purposes.

    Query Parameters:
    - category: Filter by category (metrics, cardio, exercise, sleep, recovery)
    - fact_type: Filter by type (definition, guideline, relationship)
    - limit: Maximum number of facts to return (default: 50, max: 200)

    Returns list of facts with:
    - fact: The factual statement
    - fact_type: Type of fact
    - category: Health category
    - context: Additional context
    - source: Authoritative source
    - confidence: Confidence level (high/medium)
    - last_verified: When fact was last verified

    Use this to audit individual facts and ensure accuracy.
    """
    correlation_id = generate_correlation_id()

    # Validate limit
    limit = min(max(1, limit), 200)

    try:
        from ..utils.redis_keys import RedisKeys

        # Use raw Redis client (decode_responses=False to handle binary embeddings)
        redis_client = get_redis_client()

        try:
            # Build pattern based on filters
            if category and fact_type:
                pattern = f"{RedisKeys.SEMANTIC_PREFIX}{category}:{fact_type}:*"
            elif category:
                pattern = f"{RedisKeys.SEMANTIC_PREFIX}{category}:*"
            else:
                pattern = f"{RedisKeys.SEMANTIC_PREFIX}*"

            cursor = 0
            facts = []

            while len(facts) < limit:
                cursor, keys = redis_client.scan(cursor, match=pattern, count=100)

                for key in keys:
                    if len(facts) >= limit:
                        break

                    try:
                        fact_data = redis_client.hgetall(key)

                        # Helper to get string value (handle both bytes and str)
                        def get_str_value(data, field, default=""):
                            value = data.get(field.encode(), data.get(field, default))
                            if isinstance(value, bytes):
                                return value.decode()
                            return str(value) if value else default

                        # Parse metadata
                        import json

                        metadata_str = get_str_value(fact_data, "metadata", "{}")
                        metadata = json.loads(metadata_str)

                        fact_obj = {
                            "fact": get_str_value(fact_data, "fact"),
                            "fact_type": get_str_value(fact_data, "fact_type"),
                            "category": get_str_value(fact_data, "category"),
                            "context": get_str_value(fact_data, "context"),
                            "source": get_str_value(fact_data, "source"),
                            "confidence": metadata.get("confidence", "unknown"),
                            "last_verified": metadata.get("last_verified", "unknown"),
                            "timestamp": float(
                                get_str_value(fact_data, "timestamp", "0")
                            ),
                        }

                        # Apply fact_type filter if specified
                        if fact_type and fact_obj["fact_type"] != fact_type:
                            continue

                        facts.append(fact_obj)

                    except Exception as e:
                        logger.warning(f"Failed to parse fact {key}: {e}")
                        continue

                if cursor == 0:
                    break

            # Sort by timestamp (most recent first)
            facts.sort(key=lambda x: x["timestamp"], reverse=True)

            return {
                "facts": facts,
                "count": len(facts),
                "filters": {
                    "category": category,
                    "fact_type": fact_type,
                    "limit": limit,
                },
                "description": "Semantic memory facts for audit purposes",
            }

        finally:
            redis_client.close()

    except Exception as e:
        logger.error(f"Failed to get semantic facts: {e}", exc_info=True)
        error_response = service_error(
            service="semantic_memory",
            reason=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=503, detail=error_response.dict()) from e


@router.get("/memory/semantic/search")
async def search_semantic_knowledge(
    query: str, categories: str | None = None, top_k: int = 5
):
    """
    Search semantic knowledge base with vector similarity.

    Query Parameters:
    - query: Search query (e.g., "heart rate zones", "VO2 max")
    - categories: Comma-separated categories to filter (e.g., "cardio,metrics")
    - top_k: Number of results to return (default: 5, max: 20)

    Returns:
    - context: Formatted context string with facts
    - hits: Number of facts found
    - facts: List of matching facts with metadata

    Use this to test semantic memory retrieval and verify facts
    are being retrieved correctly for user queries.
    """
    correlation_id = generate_correlation_id()

    # Validate top_k
    top_k = min(max(1, top_k), 20)

    try:
        from ..services.semantic_memory_manager import get_semantic_memory_manager

        semantic_manager = get_semantic_memory_manager()

        # Parse categories
        category_list = None
        if categories:
            category_list = [cat.strip() for cat in categories.split(",")]

        # Search semantic memory
        result = await semantic_manager.retrieve_semantic_knowledge(
            query=query,
            categories=category_list,
            top_k=top_k,
        )

        return {
            "query": query,
            "filters": {
                "categories": category_list,
                "top_k": top_k,
            },
            "result": result,
            "description": "Semantic search results using vector similarity",
        }

    except Exception as e:
        logger.error(f"Failed to search semantic knowledge: {e}", exc_info=True)
        error_response = service_error(
            service="semantic_memory",
            reason=str(e),
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=503, detail=error_response.dict()) from e
