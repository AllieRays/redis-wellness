"""Main FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router
from src.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Redis Wellness",
    description="Private wellness conversations with Redis memory, health data, and local AI",
    version="0.1.0",
)

# CORS middleware for frontend (served on :3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Redis Wellness API", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app", host=settings.app_host, port=settings.app_port, reload=True
    )
