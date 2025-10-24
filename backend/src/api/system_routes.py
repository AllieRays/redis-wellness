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
