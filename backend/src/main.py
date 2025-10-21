"""Main FastAPI application with production-ready features."""

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import get_settings

# from src.middleware.rate_limit import RateLimitMiddleware
# from src.monitoring.metrics import get_metrics, metrics_collector

settings = get_settings()

app = FastAPI(
    title="Redis Wellness AI Agent",
    description="Privacy-first wellness AI agent with Redis-powered conversational memory and secure health data analysis",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add production middleware

# # Rate limiting middleware (Redis-backed) - temporarily disabled
# app.add_middleware(RateLimitMiddleware)

# # HTTP metrics middleware - temporarily disabled
# @app.middleware("http")
# async def metrics_middleware(request: Request, call_next):
#     """Collect HTTP metrics for monitoring."""
#     start_time = time.time()
#
#     response = await call_next(request)
#
#     # Record HTTP metrics
#     duration = time.time() - start_time
#     metrics_collector.record_http_request(
#         method=request.method,
#         endpoint=request.url.path,
#         status_code=response.status_code,
#         duration=duration
#     )
#
#     return response

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

# Include API routes
app.include_router(router, prefix="/api")


# # Monitoring endpoints - temporarily disabled
# @app.get("/metrics", response_class=PlainTextResponse)
# async def prometheus_metrics():
#     """Prometheus metrics endpoint for monitoring."""
#     return get_metrics()


@app.get("/health")
async def health_check():
    """Simple health check for load balancers."""
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
            "TTL-based short-term memory (7 days)",
            "Production-ready monitoring",
            "Rate limiting and circuit breakers",
        ],
        "docs": "/docs",
        # "metrics": "/metrics"  # temporarily disabled
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app", host=settings.app_host, port=settings.app_port, reload=True
    )
