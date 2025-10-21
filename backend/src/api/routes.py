"""
Main API routes for Redis Wellness AI Agent Application.

Integrates AI agent tool calling with traditional HTTP endpoints for frontend support.
"""

import logging
import os

import httpx
import redis
from fastapi import APIRouter
from pydantic import BaseModel

from .agent_routes import router as agent_router
from .chat_routes import router as chat_router

logger = logging.getLogger(__name__)
router = APIRouter()

# Include AI agent routes
router.include_router(agent_router)

# Include chat comparison routes
router.include_router(chat_router)


# Health check models
class HealthCheck(BaseModel):
    status: str
    redis_connected: bool
    ollama_connected: bool
    ai_agent_ready: bool


def get_redis_client():
    """Get Redis client for health checks."""
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0,
        decode_responses=True,
    )


async def check_ollama_connection() -> bool:
    """Check if Ollama is accessible for AI agent functionality."""
    try:
        from ..config import get_settings

        settings = get_settings()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def check_redis_connection(redis_client) -> bool:
    """Check if Redis is accessible for TTL-based memory."""
    try:
        redis_client.ping()
        return True
    except Exception:
        return False


def check_ai_agent_ready() -> bool:
    """Check if AI agent tools are properly loaded."""
    try:
        from ..tools import AVAILABLE_TOOLS

        return len(AVAILABLE_TOOLS) > 0
    except Exception:
        return False


@router.get("/health/check", response_model=HealthCheck)
async def health_check():
    """
    Health check endpoint for AI agent system.

    Verifies that all components needed for the AI agent are working:
    - Redis for TTL-based memory
    - Ollama for local AI
    - AI agent tools loaded
    """
    redis_client = get_redis_client()

    redis_ok = await check_redis_connection(redis_client)
    ollama_ok = await check_ollama_connection()
    agent_ready = check_ai_agent_ready()

    status = "healthy" if redis_ok and ollama_ok and agent_ready else "unhealthy"

    return HealthCheck(
        status=status,
        redis_connected=redis_ok,
        ollama_connected=ollama_ok,
        ai_agent_ready=agent_ready,
    )


# Simple chat endpoint that can call AI agent tools
class ChatMessage(BaseModel):
    message: str
    user_id: str = "demo_user"
    session_id: str = "default"


class ChatResponse(BaseModel):
    response: str
    session_id: str
    ai_agent_used: bool = True


@router.post("/chat", response_model=ChatResponse)
async def ai_agent_chat(message: ChatMessage):
    """
    LangGraph-powered AI Agent chat endpoint.

    Uses sophisticated multi-step reasoning to:
    1. Analyze user queries intelligently
    2. Plan and execute multi-tool workflows
    3. Maintain conversation state across sessions
    4. Provide context-aware health insights
    """
    try:
        # Import here to avoid circular imports
        from ..agents.health_agent import process_health_conversation

        # Process through LangGraph workflow
        response = await process_health_conversation(
            message=message.message,
            user_id=message.user_id,
            session_id=message.session_id,
        )

        return ChatResponse(
            response=response, session_id=message.session_id, ai_agent_used=True
        )

    except Exception as e:
        # Fallback to simple response if LangGraph fails
        logger.error(f"LangGraph agent failed: {str(e)}")

        fallback_response = f"""I'm experiencing some technical difficulties with my advanced reasoning, but I can still help!

🔧 **I have access to powerful health tools:**
- Parse Apple Health data securely
- Store data with Redis 7-day TTL memory
- Query metrics with O(1) speed
- Generate intelligent health insights

📊 **Redis Advantages I can demonstrate:**
- Automatic TTL expiration vs manual cleanup
- Instant lookups vs slow file parsing
- Persistent conversation memory

Try asking about your "health data" or "BMI trends"!

Error details: {str(e)[:100]}..."""

        return ChatResponse(
            response=fallback_response,
            session_id=message.session_id,
            ai_agent_used=False,
        )
