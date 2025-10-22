"""Main FastAPI application with production-ready features."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.system_routes import router
from src.config import get_settings
from src.utils.api_errors import setup_exception_handlers

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


# Note: Production health checks now handled by /api/health endpoints
# This endpoint maintained for backward compatibility
@app.get("/health")
async def basic_health_check():
    """Basic health check for backward compatibility."""
    return {"status": "healthy", "timestamp": time.time()}


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
