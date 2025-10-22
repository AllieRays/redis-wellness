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
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from .chat_routes import router as chat_router
from .tools_routes import router as tools_router

logger = logging.getLogger(__name__)

# ========== Router Setup ==========

router = APIRouter()

router.include_router(chat_router)
router.include_router(tools_router)


# ========== Health Check Models ==========


class HealthCheck(BaseModel):
    """Simple system health check response."""

    model_config = ConfigDict(populate_by_name=True)

    status: str
    redis_connected: bool
    ollama_connected: bool


# ========== System Dependency Checks ==========


def get_redis_client() -> redis.Redis:
    """Create Redis client for health checks."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=int(os.getenv("REDIS_DB", 0)),
        decode_responses=True,
    )


async def check_redis_connection() -> bool:
    """Check if Redis is reachable."""
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        return True
    except Exception:
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
    Simple health check for the wellness app frontend.

    Checks if Redis and Ollama are running - that's all we need.
    """
    redis_ok = await check_redis_connection()
    ollama_ok = await check_ollama_connection()

    status = "healthy" if redis_ok and ollama_ok else "unhealthy"

    return HealthCheck(
        status=status, redis_connected=redis_ok, ollama_connected=ollama_ok
    )


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
    from ..services.embedding_cache import get_embedding_cache

    cache = get_embedding_cache()
    stats = cache.get_stats()

    return {
        "embedding_cache": stats,
        "description": "Embedding cache statistics (caches Ollama embedding generation)",
        "note": "High hit rate = faster semantic memory searches",
    }
