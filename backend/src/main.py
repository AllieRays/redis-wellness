"""Main FastAPI application with production-ready features."""

import time
from typing import Any

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.system_routes import router
from .config import get_settings
from .logging_config import setup_logging
from .services.redis_connection import get_redis_manager
from .utils.api_errors import setup_exception_handlers

# Setup logging with datetime stamps
setup_logging()

settings = get_settings()

app = FastAPI(
    title="Redis Wellness AI Agent",
    description="Privacy-first wellness AI agent with Redis-powered conversational memory and secure health data analysis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware for frontend (served on :3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",
        "http://127.0.0.1:3000",  # Alternative localhost
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Setup production error handling
setup_exception_handlers(app)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """
    Comprehensive health check including dependencies.

    Checks:
    - API responsiveness
    - Redis connectivity
    - Ollama availability and required models

    Returns:
        Health status dict with overall status and dependency details
    """
    status: dict[str, Any] = {
        "api": "healthy",
        "timestamp": time.time(),
        "dependencies": {},
    }

    # Check Redis
    try:
        redis_manager = get_redis_manager()
        with redis_manager.get_connection() as client:
            client.ping()
            status["dependencies"]["redis"] = {
                "status": "healthy",
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
    except Exception as e:
        status["dependencies"]["redis"] = {"status": "unhealthy", "error": str(e)}

    # Check Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            models_data = response.json().get("models", [])
            required_models = [settings.ollama_model, settings.embedding_model]
            available = [m["name"] for m in models_data]

            # Check if required models are available
            all_models_available = all(
                any(req in avail for avail in available) for req in required_models
            )

            status["dependencies"]["ollama"] = {
                "status": "healthy" if all_models_available else "degraded",
                "url": settings.ollama_base_url,
                "models_required": required_models,
                "models_available": available,
                "models_missing": [
                    req
                    for req in required_models
                    if not any(req in avail for avail in available)
                ]
                if not all_models_available
                else [],
            }
    except httpx.TimeoutException:
        status["dependencies"]["ollama"] = {
            "status": "unhealthy",
            "error": "Connection timeout",
        }
    except httpx.HTTPStatusError as e:
        status["dependencies"]["ollama"] = {
            "status": "unhealthy",
            "error": f"HTTP {e.response.status_code}",
        }
    except Exception as e:
        status["dependencies"]["ollama"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(
        dep.get("status") == "healthy" for dep in status["dependencies"].values()
    )
    status["status"] = "healthy" if all_healthy else "degraded"

    return status


@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "message": "Redis Wellness AI Agent",
        "version": "0.1.0",
        "features": [
            "Privacy-first health data parsing",
            "Redis-powered conversational memory",
            "RedisVL semantic search with HNSW index",
            "Dual memory system (short + long term)",
            "Local-first with Ollama (no cloud APIs)",
        ],
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app", host=settings.app_host, port=settings.app_port, reload=True
    )
